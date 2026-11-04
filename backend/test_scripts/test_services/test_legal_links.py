"""
The legal links of the instance (workstream A, lot A9: F09): its terms of service and its privacy policy.

Under test: ``tos_url()`` and ``privacy_url()``, new in ``backend/app/config/platform.py`` beside ``support_url()``, and
``terms_link()`` and ``privacy_link()``, new in ``backend/app/services/platform/instance_links.py`` beside
``support_link()``: what ``GET /system/instance`` publishes as ``legal.terms_url`` and ``legal.privacy_url``
(``test_api/test_instance_config_legal_api.py``). The contract:

1. ``tos_url()`` reads ``LIBREFOLIO_TOS_URL`` and ``privacy_url()`` reads ``LIBREFOLIO_PRIVACY_URL``, each through
   ``env_url()``, the rule of every address variable, as ``support_url()`` reads an http(s) support address: unset,
   empty or blank is ``None``; a valid http(s) address is the value ``env_url()`` gives (stripped, one trailing slash
   removed, nothing else changed); any other value raises ``ValueError`` naming the variable: no scheme, another scheme
   (``ftp:``, ``javascript:``, and ``mailto:``, which the support address alone takes), no host, whitespace inside.
2. An address with user info in its authority is refused like any other invalid one, and the error holds neither its
   user name nor its password (the rule of ``env_url()``, X-R35).
3. Each accessor reads its own variable alone: the other legal variable and the support address, set and valid, leave
   it ``None``.
4. ``terms_link()`` and ``privacy_link()`` never raise: the address their accessor gives, or ``None`` when it is unset or
   invalid. Neither a missing nor a valid address is a problem: nothing is logged.
5. An invalid address is logged once per process, as ``support_link()`` logs one (``_report_invalid``, a
   ``functools.cache``): one error event, ``Invalid instance link``, whose ``problem`` names the variable (its own, not
   the other legal one) and whose ``consequence`` says that the link stays hidden until the address is fixed, in words of
   its own, not the support address's. However often it is read, one error; an invalid terms address and an invalid
   privacy address log one each.
6. No secret in the log: for an address with user info, no captured record holds its user name or its password.
7. Each link publishes its own address: with all three set, the terms link is the terms address, the privacy link the
   privacy address, and the support link still the support address.

How: pure. The variables are set with ``monkeypatch`` and restored after each case; every case starts with the three
link variables unset. No database, no server, no network. The log is read with ``structlog.testing.capture_logs``
behind a barrier: a canary logged through the module's own logger must reach the capture, or "nothing was logged"
would prove nothing. The cache of ``_report_invalid`` is emptied before and after each case, so "once per process"
starts over in each; so are the settings, should they ever be cached (they are built at each call today). The
user-info address is built from its parts, so the credentials can be searched for wherever they might leak. The four
new functions are looked up when a test runs: until A9 each test fails on its own with «red until A9: …», never the
collection. Texts and names that may still change are constants at the top.
"""

from __future__ import annotations

import contextlib
from collections.abc import Callable, Iterator
from typing import Any, NamedTuple
from urllib.parse import urlsplit

import pytest
from structlog.testing import capture_logs

from backend.app import config
from backend.app.config import env_url
from backend.app.config import platform as platform_config
from backend.app.services.platform import instance_links
from backend.test_scripts.test_utils import print_section, print_success

TOS_VARIABLE = "LIBREFOLIO_TOS_URL"
PRIVACY_VARIABLE = "LIBREFOLIO_PRIVACY_URL"
SUPPORT_VARIABLE = "LIBREFOLIO_SUPPORT_URL"
#: The one event an invalid instance link logs (``services/platform/instance_links.py``).
INVALID_INSTANCE_LINK = "Invalid instance link"
#: The words, in any case, of the consequence an invalid legal link logs: the link stays hidden until it is fixed.
LEGAL_CONSEQUENCE_WORDS = ("hidden", "until", "fixed")
LINK_LOG_CANARY = "canary: the capture reaches the logger of the instance links"

#: A valid address for each variable, all different: a link that publishes another variable's address is caught.
SAMPLES = {
    TOS_VARIABLE: "https://legal.example.org/terms",
    PRIVACY_VARIABLE: "https://legal.example.org/privacy",
    SUPPORT_VARIABLE: "https://help.example.org/support",
}
#: The user name and the password of the user-info cases, distinctive enough that either one found in a message or a log
#: record can only be the value leaking; the address is built from them, never written whole.
USER_INFO_NAME = "alice-legal"
USER_INFO_PASSWORD = "t0s-s3cr3t-pw"
USER_INFO_ADDRESS = f"https://{USER_INFO_NAME}:{USER_INFO_PASSWORD}@legal.example.org/terms"


class LegalLink(NamedTuple):
    """One legal link: its reader in ``config/platform.py``, its publisher in ``instance_links.py``, its variable, and the other legal variable."""

    accessor: str
    link: str
    variable: str
    other_variable: str


TERMS = LegalLink("tos_url", "terms_link", TOS_VARIABLE, PRIVACY_VARIABLE)
PRIVACY = LegalLink("privacy_url", "privacy_link", PRIVACY_VARIABLE, TOS_VARIABLE)
LEGAL_LINKS = [pytest.param(TERMS, id="terms"), pytest.param(PRIVACY, id="privacy")]

#: (1) Valid http(s) addresses and what ``env_url()`` makes of them.
VALID_ADDRESSES = [
    pytest.param("https://legal.example.org/terms", "https://legal.example.org/terms", id="https"),
    pytest.param(" https://legal.example.org/terms/ \n", "https://legal.example.org/terms", id="stripped-without-its-trailing-slash"),
    pytest.param("HTTP://Legal.Example.ORG/Privacy", "HTTP://Legal.Example.ORG/Privacy", id="http-any-case-the-case-kept"),
    pytest.param("http://192.168.1.20:6040/legal/", "http://192.168.1.20:6040/legal", id="ipv4-with-a-port"),
    pytest.param("https://legal.example.org/doc?lang=it#privacy", "https://legal.example.org/doc?lang=it#privacy", id="query-and-fragment-kept"),
]
#: (1) Values that are no http(s) address with a host.
INVALID_ADDRESSES = [
    pytest.param("legal.example.org/terms", id="no-scheme"),
    pytest.param("ftp://legal.example.org/terms", id="ftp"),
    pytest.param("mailto:legal@example.org", id="mailto-the-support-address-alone-takes-it"),
    pytest.param("javascript:alert(1)", id="javascript"),
    pytest.param("https://", id="no-host"),
    pytest.param("https://legal.example.org/terms of use", id="space-inside"),
]


# =============================================================================
# HELPERS
# =============================================================================


def _accessor(legal: LegalLink) -> Callable[[], str | None]:
    """The reader of ``legal.variable`` in ``config/platform.py``, looked up when the test runs."""
    function = getattr(platform_config, legal.accessor, None)
    assert callable(function), f"red until A9: backend.app.config.platform has no {legal.accessor}(), the reader of {legal.variable} (found {function!r})"
    return function


def _link(legal: LegalLink) -> Callable[[], str | None]:
    """The publisher of ``legal.variable`` in ``instance_links.py``, looked up when the test runs."""
    function = getattr(instance_links, legal.link, None)
    assert callable(function), f"red until A9: backend.app.services.platform.instance_links has no {legal.link}(), the published {legal.variable} (found {function!r})"
    return function


def _forget_cached_state() -> None:
    """The settings (should they ever be cached) and the once-per-process log of an invalid instance link start over."""
    settings_cache_clear = getattr(config.get_settings, "cache_clear", None)
    if callable(settings_cache_clear):
        settings_cache_clear()
    report = getattr(instance_links, "_report_invalid", None)
    report_cache_clear = getattr(report, "cache_clear", None)
    assert callable(report_cache_clear), f"the once-per-process log of an invalid instance link cannot start over: instance_links._report_invalid is {report!r}, without cache_clear"
    report_cache_clear()


@pytest.fixture(autouse=True)
def fresh_link_state(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """The three link variables unset, the caches empty, before the case; the caches empty after it: no case inherits what another set or reported."""
    for name in SAMPLES:
        monkeypatch.delenv(name, raising=False)
    _forget_cached_state()
    yield
    _forget_cached_state()


def _set_variable(monkeypatch: pytest.MonkeyPatch, name: str, value: str | None) -> None:
    """``None`` unsets ``name``; any string, the empty one included, sets it."""
    if value is None:
        monkeypatch.delenv(name, raising=False)
    else:
        monkeypatch.setenv(name, value)


def _user_info_in(text: str) -> list[str]:
    """The parts of the user info that ``text`` holds, in any case: anything but ``[]`` is the value leaking."""
    return [part for part in (USER_INFO_NAME, USER_INFO_PASSWORD) if part.casefold() in text.casefold()]


@contextlib.contextmanager
def _captured_link_log() -> Iterator[list[dict[str, Any]]]:
    """The structlog events of the block, behind a barrier: a canary logged through the module's own logger must be among them."""
    with capture_logs() as events:
        instance_links.logger.debug(LINK_LOG_CANARY)
        yield events
    assert any(event.get("event") == LINK_LOG_CANARY for event in events), f"barrier: the events of the instance links' logger do not reach capture_logs, so what this test reads of the log proves nothing: {events}"


def _error_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The error-level events among those captured: what an operator's log shows as a problem."""
    return [event for event in events if event.get("log_level") in ("error", "critical")]


# =============================================================================
# 1-3. THE READERS: tos_url() AND privacy_url(), BY THE RULE OF env_url()
# =============================================================================


# red until A9: config/platform.py has no tos_url() nor privacy_url()
@pytest.mark.parametrize("value", [pytest.param(None, id="unset"), pytest.param("", id="empty"), pytest.param("   ", id="blank"), pytest.param(" \t\n", id="any-whitespace")])
@pytest.mark.parametrize("legal", LEGAL_LINKS)
def test_the_reader_is_none_when_its_variable_is_unset_or_blank(monkeypatch: pytest.MonkeyPatch, legal: LegalLink, value: str | None) -> None:
    """LGL-001 (1): unset, empty or blank sets no address: ``None``."""
    print_section(f"LGL-001: {legal.variable}={value!r}")
    accessor = _accessor(legal)
    _set_variable(monkeypatch, legal.variable, value)

    address = accessor()

    assert address is None, f"{legal.variable}={value!r} sets no address: {legal.accessor}() must give None, gave {address!r}"
    print_success(f"{legal.variable}={value!r}: {legal.accessor}() is None")


# red until A9: config/platform.py has no tos_url() nor privacy_url()
@pytest.mark.parametrize(("value", "expected"), VALID_ADDRESSES)
@pytest.mark.parametrize("legal", LEGAL_LINKS)
def test_the_reader_gives_a_valid_address_as_env_url_gives_it(monkeypatch: pytest.MonkeyPatch, legal: LegalLink, value: str, expected: str) -> None:
    """LGL-002 (1): a valid http(s) address is the value ``env_url()`` gives: stripped, one trailing slash removed, the case, the query and the fragment kept."""
    print_section(f"LGL-002: {legal.variable}={value!r}")
    accessor = _accessor(legal)
    monkeypatch.setenv(legal.variable, value)

    address = accessor()

    assert address == expected, f"{legal.variable}={value!r}: {legal.accessor}() must give {expected!r}, gave {address!r}"
    assert address == env_url(legal.variable), f"{legal.variable}={value!r}: {legal.accessor}() must give what env_url() gives, {env_url(legal.variable)!r}, gave {address!r}"
    print_success(f"{legal.variable}={value!r}: {legal.accessor}() == {address!r}")


# red until A9: config/platform.py has no tos_url() nor privacy_url()
@pytest.mark.parametrize("value", INVALID_ADDRESSES)
@pytest.mark.parametrize("legal", LEGAL_LINKS)
def test_the_reader_raises_naming_its_variable_on_anything_but_an_http_address(monkeypatch: pytest.MonkeyPatch, legal: LegalLink, value: str) -> None:
    """LGL-003 (1): anything but an http(s) address with a host, ``mailto:`` included, raises ``ValueError`` naming the variable: the reader never guesses, and the link decides what it costs."""
    print_section(f"LGL-003: {legal.variable}={value!r}")
    accessor = _accessor(legal)
    monkeypatch.setenv(legal.variable, value)

    with pytest.raises(ValueError, match=legal.variable) as raised:
        accessor()

    print_success(f"{legal.variable}={value!r}: {raised.value}")


# red until A9: config/platform.py has no tos_url() nor privacy_url()
@pytest.mark.parametrize("legal", LEGAL_LINKS)
def test_the_reader_refuses_user_info_and_never_quotes_it(monkeypatch: pytest.MonkeyPatch, legal: LegalLink) -> None:
    """LGL-004 (2): user info in the authority is an error naming the variable, whose message holds neither the user name nor the password."""
    print_section(f"LGL-004: {legal.variable} with user info")
    accessor = _accessor(legal)
    assert "@" in urlsplit(USER_INFO_ADDRESS).netloc, f"precondition: {USER_INFO_ADDRESS!r} must hold user info, an @ in its authority"
    monkeypatch.setenv(legal.variable, USER_INFO_ADDRESS)

    with pytest.raises(ValueError, match=legal.variable) as raised:
        accessor()

    assert _user_info_in(str(raised.value)) == [], f"the error must name {legal.variable} without quoting its user info, neither {USER_INFO_NAME!r} nor {USER_INFO_PASSWORD!r}: {raised.value}"
    print_success(f"{legal.variable}: refused without its user info: {raised.value}")


# red until A9: config/platform.py has no tos_url() nor privacy_url()
@pytest.mark.parametrize("legal", LEGAL_LINKS)
def test_each_reader_reads_its_own_variable_alone(monkeypatch: pytest.MonkeyPatch, legal: LegalLink) -> None:
    """LGL-005 (3): the other legal variable and the support address, set and valid, leave the reader ``None``; its own variable set, it gives its own address."""
    print_section(f"LGL-005: {legal.accessor}() reads {legal.variable} alone")
    accessor = _accessor(legal)
    monkeypatch.setenv(legal.other_variable, SAMPLES[legal.other_variable])
    monkeypatch.setenv(SUPPORT_VARIABLE, SAMPLES[SUPPORT_VARIABLE])

    without_its_own = accessor()
    monkeypatch.setenv(legal.variable, SAMPLES[legal.variable])
    with_its_own = accessor()

    assert without_its_own is None, f"{legal.variable} unset: {legal.accessor}() must give None whatever {legal.other_variable} and {SUPPORT_VARIABLE} say, gave {without_its_own!r}"
    assert with_its_own == SAMPLES[legal.variable], f"{legal.variable} set: {legal.accessor}() must give its own address {SAMPLES[legal.variable]!r}, gave {with_its_own!r}"
    print_success(f"{legal.accessor}(): None without {legal.variable}, {with_its_own!r} with it")


# =============================================================================
# 4-7. THE PUBLISHED LINKS: terms_link() AND privacy_link(), NEVER RAISING
# =============================================================================


# red until A9: instance_links.py has no terms_link() nor privacy_link()
@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param(None, None, id="unset-is-no-link"),
        pytest.param("  ", None, id="blank-is-no-link"),
        pytest.param(" https://legal.example.org/doc/ ", "https://legal.example.org/doc", id="valid-is-the-address"),
    ],
)
@pytest.mark.parametrize("legal", LEGAL_LINKS)
def test_the_link_is_the_address_and_logs_nothing(monkeypatch: pytest.MonkeyPatch, legal: LegalLink, value: str | None, expected: str | None) -> None:
    """LGL-006 (4): the address of the variable, ``None`` without one; neither is a problem: no error is logged."""
    print_section(f"LGL-006: {legal.link}() with {legal.variable}={value!r}")
    link = _link(legal)
    _set_variable(monkeypatch, legal.variable, value)

    with _captured_link_log() as events:
        published = link()

    assert published == expected, f"{legal.variable}={value!r}: {legal.link}() must give {expected!r}, gave {published!r}"
    assert _error_events(events) == [], f"a missing or a valid {legal.variable} is no problem to report: {_error_events(events)}"
    print_success(f"{legal.variable}={value!r}: {legal.link}() == {published!r}, nothing logged")


# red until A9: instance_links.py has no terms_link() nor privacy_link()
@pytest.mark.parametrize("value", INVALID_ADDRESSES)
@pytest.mark.parametrize("legal", LEGAL_LINKS)
def test_an_invalid_link_is_no_link_and_one_error_however_often_it_is_read(monkeypatch: pytest.MonkeyPatch, legal: LegalLink, value: str) -> None:
    """LGL-007 (4, 5): an invalid address never raises out of the link: no link at every reading, and one error for the whole process, ``Invalid instance link``, whose ``problem`` names the variable and whose ``consequence`` says the link stays hidden until it is fixed."""
    print_section(f"LGL-007: {legal.link}() with {legal.variable}={value!r}")
    link = _link(legal)
    monkeypatch.setenv(legal.variable, value)

    with _captured_link_log() as events:
        published = [link(), link()]

    errors = _error_events(events)
    assert published == [None, None], f"{legal.variable}={value!r}: every reading must give no link, got {published}"
    assert [error.get("event") for error in errors] == [INVALID_INSTANCE_LINK], f"two readings of an invalid {legal.variable} must log exactly one error, {INVALID_INSTANCE_LINK!r}: {errors}"
    problem = str(errors[0].get("problem"))
    assert legal.variable in problem and legal.other_variable not in problem, f"the problem must name {legal.variable}, and not {legal.other_variable}: {problem!r}"
    consequence = str(errors[0].get("consequence") or "")
    missing = [word for word in LEGAL_CONSEQUENCE_WORDS if word not in consequence.casefold()]
    assert missing == [], f"the consequence must say the link stays hidden until the address is fixed (the words {LEGAL_CONSEQUENCE_WORDS}, in any case), missing {missing}: {consequence!r}"
    support_consequence = getattr(instance_links, "_DEFAULT_SUPPORT", None)
    assert consequence != support_consequence, f"the consequence of an invalid {legal.variable} is its own, not the support address's: {consequence!r}"
    print_success(f"{legal.variable}={value!r}: no link twice, one error: {problem} / {consequence}")


# red until A9: instance_links.py has no terms_link() nor privacy_link()
@pytest.mark.parametrize("legal", LEGAL_LINKS)
def test_a_link_with_user_info_is_no_link_and_no_log_record_holds_it(monkeypatch: pytest.MonkeyPatch, legal: LegalLink) -> None:
    """LGL-008 (2, 6): an address with user info is invalid like any other: no link at every reading, one error naming the variable, and no captured record holds the user name or the password.

    The one error, and the canary of the capture, are the presence barriers that give that absence its meaning.
    """
    print_section(f"LGL-008: {legal.link}() with {legal.variable} holding user info")
    link = _link(legal)
    monkeypatch.setenv(legal.variable, USER_INFO_ADDRESS)

    with _captured_link_log() as events:
        published = [link(), link()]

    errors = _error_events(events)
    assert published == [None, None], f"{legal.variable} with user info: every reading must publish no link, got {published}"
    assert [error.get("event") for error in errors] == [INVALID_INSTANCE_LINK], f"two readings of {legal.variable} with user info must log exactly one error, {INVALID_INSTANCE_LINK!r}: {errors}"
    assert legal.variable in str(errors[0].get("problem")), f"the problem must name {legal.variable}: {errors[0]}"
    leaking = [event for event in events if _user_info_in(repr(event))]
    assert leaking == [], f"no log record may hold the user name {USER_INFO_NAME!r} or the password {USER_INFO_PASSWORD!r}: {leaking}"
    print_success(f"{legal.variable} with user info: no link twice, one error without the credentials")


# red until A9: instance_links.py has no terms_link() nor privacy_link()
def test_an_invalid_terms_address_and_an_invalid_privacy_address_log_one_error_each(monkeypatch: pytest.MonkeyPatch) -> None:
    """LGL-009 (5): both invalid, each read twice: no link at any reading, and exactly two errors, one naming each variable: one invalid link never silences the other."""
    print_section("LGL-009: both legal addresses invalid")
    terms_link, privacy_link = _link(TERMS), _link(PRIVACY)
    monkeypatch.setenv(TOS_VARIABLE, "ftp://legal.example.org/terms")
    monkeypatch.setenv(PRIVACY_VARIABLE, "legal.example.org/privacy")

    with _captured_link_log() as events:
        published = [terms_link(), privacy_link(), terms_link(), privacy_link()]

    errors = _error_events(events)
    assert published == [None, None, None, None], f"every reading of an invalid legal address must give no link, got {published}"
    named = sorted(tuple(variable for variable in (TOS_VARIABLE, PRIVACY_VARIABLE) if variable in str(error.get("problem"))) for error in errors)
    assert [error.get("event") for error in errors] == [INVALID_INSTANCE_LINK, INVALID_INSTANCE_LINK] and named == [(PRIVACY_VARIABLE,), (TOS_VARIABLE,)], f"exactly one {INVALID_INSTANCE_LINK!r} per invalid variable, each naming its own: {errors}"
    print_success("both invalid: no link at any reading, one error each")


# red until A9: instance_links.py has no terms_link() nor privacy_link()
def test_each_link_publishes_its_own_address(monkeypatch: pytest.MonkeyPatch) -> None:
    """LGL-010 (7): the three link variables set to different valid addresses: each link its own address, the support link unchanged, nothing logged."""
    print_section("LGL-010: terms, privacy and support addresses set")
    terms_link, privacy_link = _link(TERMS), _link(PRIVACY)
    for name, address in SAMPLES.items():
        monkeypatch.setenv(name, address)

    with _captured_link_log() as events:
        published = {TOS_VARIABLE: terms_link(), PRIVACY_VARIABLE: privacy_link(), SUPPORT_VARIABLE: instance_links.support_link()}

    assert published == SAMPLES, f"each link must publish its own variable's address: expected {SAMPLES}, got {published}"
    assert _error_events(events) == [], f"three valid addresses are no problem to report: {_error_events(events)}"
    print_success(f"each link its own address: {published}")
