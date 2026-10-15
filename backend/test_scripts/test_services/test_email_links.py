"""``backend.app.services.email.links``: every link an email carries comes from ``LIBREFOLIO_PUBLIC_URL`` alone (plan phase01Email §3 E3, developer decision 45, lot E3).

A link inside an email — a forgotten password, an invitation or a reset link an administrator sends — is built from the
public address of the instance and the token, never from a request: a stranger could otherwise have a real token mailed
to a user inside a link to a site of theirs. Without ``LIBREFOLIO_PUBLIC_URL``, no email with a link goes out. The
contract pinned here:

1. ``links_state()`` reads ``LIBREFOLIO_PUBLIC_URL`` now and never raises: unset or blank is ``PUBLIC_URL_MISSING``
   with no base; a value that is not an http(s) address, or an http(s) address no link can start from — no host, a
   space or a tab inside, a ``?`` or a ``#`` anywhere (even with nothing after it), a port out of range or not a
   number, credentials, a bracket the URL parser cannot read (``https://[::1``: never an exception) —, is
   ``PUBLIC_URL_INVALID`` with no base — the value is never echoed —; an http(s) address is
   ready, its base stripped of the spaces around it and of one trailing slash, a path prefix kept as written, the
   scheme in any case, the host a name or an IP literal (IPv6 in brackets). ``ready`` is a base without a problem.
2. ``LinksState.instance`` is how an email names the instance: the host of the base with its port, no scheme, no path;
   empty without a base.
3. ``require_links()`` returns the ready state, else raises ``EmailLinksUnavailableError`` — an ``EmailError`` — whose
   code is the problem.
4. ``email_link(purpose, token)`` takes the purpose and the token and nothing else (no request, no host): it is exactly
   the base, the page of the purpose (``/reset-password``, ``/invite``) and the token urlencoded in the fragment, which
   reads back as the token; nothing in the query. Without a usable base it raises ``EmailLinksUnavailableError`` with
   the problem — for an address no link can start from too: never a bare ``ValueError`` from the message builders.
5. ``email_instance_config()``, the email part of ``GET /system/instance``: ``available`` is whether email can be used
   and the instance is not blocked (``LIBREFOLIO_BLOCKED`` blocking, or unreadable), ``links`` whether it is available
   and links are ready — in the four combinations, with an unusable configuration, and on a blocked instance.

Pure: no database, no server, no network. An autouse fixture removes every inherited ``LIBREFOLIO_SMTP_*``,
``LIBREFOLIO_PUBLIC_URL`` and ``LIBREFOLIO_BLOCKED`` (C-96 removes them from the lanes; a developer's shell may still
carry them); each test sets its own with ``monkeypatch``.
"""

from __future__ import annotations

import inspect
import os
from collections.abc import Iterator
from urllib.parse import parse_qs, urlsplit

import pytest

from backend.app.db.models import AccountTokenPurpose
from backend.app.schemas.email import EmailInstanceConfig
from backend.app.services.email import delivery
from backend.app.services.email.delivery import EmailError
from backend.app.services.email.links import EmailLinksUnavailableError, LinksState, email_instance_config, email_link, links_state, require_links
from backend.test_scripts.test_utils import print_section, print_success

SMTP_PREFIX = "LIBREFOLIO_SMTP_"
PUBLIC_URL_VARIABLE = "LIBREFOLIO_PUBLIC_URL"
#: The hosting provider's block: a blocked instance sends nothing, and says so in ``email_instance_config``.
BLOCKED_VARIABLE = "LIBREFOLIO_BLOCKED"
PUBLIC_URL = "https://folio.zq-public.example.com"
#: A usable SMTP configuration: email_config_state reads it without connecting anywhere.
USABLE_SMTP = {"LIBREFOLIO_SMTP_HOST": "smtp.zq-host.example.com", "LIBREFOLIO_SMTP_FROM": "LibreFolio <noreply@example.com>"}
#: A token as secrets.token_urlsafe makes it: nothing to encode.
TOKEN = "Zm9v_YmFy-0123456789abcdefghijklmnopqrstuv"
#: A token full of characters a URL must encode: its round trip proves the encoding.
AWKWARD_TOKEN = "a+b/c=d&e f#g?h%i"

INVALID_VALUES = ["ftp://folio.zq-public.example.com", "folio.zq-public.example.com", "//folio.zq-public.example.com", "mailto:zq-admin@example.com"]
#: http(s) addresses no link can start from: the scheme check alone would let them through.
MALFORMED_VALUES = [
    pytest.param("https://", id="the-scheme-alone"),
    pytest.param("https://:8443/folio", id="a-port-without-a-host"),
    pytest.param("https://folio.zq-space.example.com/my folio", id="a-space-inside"),
    pytest.param("https://folio.zq-tab.example.com/my\tfolio", id="a-tab-inside"),
    pytest.param("https://folio.zq-query.example.com/app?lang=it", id="a-query"),
    pytest.param("https://folio.zq-fragment.example.com/app#top", id="a-fragment"),
    pytest.param("https://folio.zq-qmark.example.com/app?", id="an-empty-query"),
    pytest.param("https://folio.zq-hash.example.com/app#", id="an-empty-fragment"),
    pytest.param("https://folio.zq-port.example.com:99999/app", id="a-port-out-of-range"),
    pytest.param("https://folio.zq-port.example.com:abc/", id="a-port-that-is-not-a-number"),
    pytest.param("https://zq-user:zq-secret@folio.example.com/app", id="credentials"),
    pytest.param("https://[::1", id="an-unclosed-ipv6-bracket"),
]


@pytest.fixture(autouse=True)
def _no_inherited_email_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every ``LIBREFOLIO_SMTP_*``, ``LIBREFOLIO_PUBLIC_URL`` and ``LIBREFOLIO_BLOCKED`` the lane inherited is removed: a test sees only what it sets itself."""
    for name in list(os.environ):
        if name.startswith(SMTP_PREFIX) or name in (PUBLIC_URL_VARIABLE, BLOCKED_VARIABLE):
            monkeypatch.delenv(name, raising=False)


@pytest.fixture(autouse=True)
def _nothing_reported_yet() -> Iterator[None]:
    """``delivery._report_invalid`` remembers for the whole process what it logged: each test starts, and leaves, with nothing reported."""
    delivery._report_invalid.cache_clear()
    yield
    delivery._report_invalid.cache_clear()


def _public_url(monkeypatch: pytest.MonkeyPatch, value: str | None) -> None:
    """``LIBREFOLIO_PUBLIC_URL`` set to ``value``, or unset for ``None``."""
    if value is None:
        monkeypatch.delenv(PUBLIC_URL_VARIABLE, raising=False)
    else:
        monkeypatch.setenv(PUBLIC_URL_VARIABLE, value)


# =============================================================================
# 1-3. links_state, instance, require_links
# =============================================================================


def test_the_functions_take_nothing_from_a_request() -> None:
    """EML-001 — contracts 1 and 4: ``links_state()`` and ``require_links()`` take no argument, ``email_link`` exactly ``(purpose, token)``: there is no way to hand them a host, an ``Origin`` or a request."""
    print_section("EML-001: signatures")

    assert list(inspect.signature(links_state).parameters) == []
    assert list(inspect.signature(require_links).parameters) == []
    assert list(inspect.signature(email_link).parameters) == ["purpose", "token"]
    print_success("links_state(), require_links(), email_link(purpose, token)")


@pytest.mark.parametrize("value", [pytest.param(None, id="unset"), pytest.param("", id="empty"), pytest.param("   ", id="blank")])
def test_without_a_public_url_links_are_missing(monkeypatch: pytest.MonkeyPatch, value: str | None) -> None:
    """EML-002 — contract 1: unset, empty or blank is ``PUBLIC_URL_MISSING``, no base, not ready, no instance."""
    print_section(f"EML-002: LIBREFOLIO_PUBLIC_URL={value!r}")
    _public_url(monkeypatch, value)

    state = links_state()

    assert (state.base, state.problem, state.ready, state.instance) == (None, "PUBLIC_URL_MISSING", False, ""), state
    print_success("missing")


@pytest.mark.parametrize("value", INVALID_VALUES)
def test_a_public_url_that_is_not_http_is_invalid_and_never_echoed(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    """EML-003 — contract 1: a value that is not an http(s) address is ``PUBLIC_URL_INVALID``, no base, not ready; ``links_state()`` does not raise and its state does not carry the value."""
    print_section(f"EML-003: LIBREFOLIO_PUBLIC_URL={value!r}")
    _public_url(monkeypatch, value)

    state = links_state()

    assert (state.base, state.problem, state.ready, state.instance) == (None, "PUBLIC_URL_INVALID", False, ""), state
    assert "zq-" not in repr(state), f"the state echoes the invalid value: {state!r}"
    print_success("invalid, not echoed")


@pytest.mark.parametrize(
    ("value", "base", "instance"),
    [
        pytest.param("https://folio.zq-public.example.com", "https://folio.zq-public.example.com", "folio.zq-public.example.com", id="https"),
        pytest.param("https://folio.zq-public.example.com/", "https://folio.zq-public.example.com", "folio.zq-public.example.com", id="trailing-slash-removed"),
        pytest.param("  https://folio.zq-public.example.com  ", "https://folio.zq-public.example.com", "folio.zq-public.example.com", id="spaces-around-removed"),
        pytest.param("http://192.168.1.10:6040", "http://192.168.1.10:6040", "192.168.1.10:6040", id="http-address-with-port"),
        pytest.param("https://zq-public.example.com:8443/folio/", "https://zq-public.example.com:8443/folio", "zq-public.example.com:8443", id="path-prefix-kept-port-in-instance"),
        pytest.param("HTTPS://Folio.ZQ-Public.Example.com", "HTTPS://Folio.ZQ-Public.Example.com", "Folio.ZQ-Public.Example.com", id="scheme-in-capitals"),
        pytest.param("http://[::1]:6040/folio", "http://[::1]:6040/folio", "[::1]:6040", id="ipv6-literal-with-port"),
        pytest.param("https://[::1]:8443/x", "https://[::1]:8443/x", "[::1]:8443", id="ipv6-literal-https"),
        pytest.param("http://localhost:6040", "http://localhost:6040", "localhost:6040", id="localhost-with-port"),
    ],
)
def test_an_http_public_url_is_ready_with_its_base_and_instance(monkeypatch: pytest.MonkeyPatch, value: str, base: str, instance: str) -> None:
    """EML-004 — contracts 1 and 2: an http(s) address is ready, no problem; the base without the spaces around it and one trailing slash, a path prefix kept, the scheme in any case, the host a name or an IP literal; the instance is the host with its port, without scheme or path."""
    print_section(f"EML-004: LIBREFOLIO_PUBLIC_URL={value!r}")
    _public_url(monkeypatch, value)

    state = links_state()

    assert (state.base, state.problem, state.ready, state.instance) == (base, None, True, instance), state
    print_success(f"base {state.base}, instance {state.instance}")


def test_links_state_reads_the_variable_at_each_call(monkeypatch: pytest.MonkeyPatch) -> None:
    """EML-005 — contract 1: missing, then set, then invalid, then unset again: each call answers the variable as it is now."""
    print_section("EML-005: read at call time")
    answers = []
    for value in (None, PUBLIC_URL, "ftp://zq-public.example.com", None):
        _public_url(monkeypatch, value)
        answers.append((links_state().ready, links_state().problem))

    assert answers == [(False, "PUBLIC_URL_MISSING"), (True, None), (False, "PUBLIC_URL_INVALID"), (False, "PUBLIC_URL_MISSING")]
    print_success("missing, ready, invalid, missing")


@pytest.mark.parametrize(
    ("value", "problem"),
    [
        pytest.param(None, "PUBLIC_URL_MISSING", id="missing"),
        pytest.param("ftp://folio.zq-public.example.com", "PUBLIC_URL_INVALID", id="invalid"),
        pytest.param(PUBLIC_URL, None, id="ready"),
    ],
)
def test_require_links_returns_the_ready_state_or_raises_its_problem(monkeypatch: pytest.MonkeyPatch, value: str | None, problem: str | None) -> None:
    """EML-006 — contract 3: ready, ``require_links()`` returns the state ``links_state()`` reads; otherwise it raises ``EmailLinksUnavailableError``, an ``EmailError``, with the problem as its code."""
    print_section(f"EML-006: require_links, {problem or 'ready'}")
    _public_url(monkeypatch, value)

    if problem is None:
        assert require_links() == links_state() == LinksState(base=PUBLIC_URL, problem=None)
    else:
        with pytest.raises(EmailLinksUnavailableError) as raised:
            require_links()
        assert isinstance(raised.value, EmailError)
        assert raised.value.code == problem
    print_success(problem or "ready")


# =============================================================================
# 4. email_link
# =============================================================================


@pytest.mark.parametrize(
    ("purpose", "page"),
    [
        pytest.param(AccountTokenPurpose.PASSWORD_RESET, "/reset-password", id="password-reset"),
        pytest.param(AccountTokenPurpose.INVITE, "/invite", id="invite"),
    ],
)
@pytest.mark.parametrize(
    ("value", "base"),
    [
        pytest.param(PUBLIC_URL, PUBLIC_URL, id="root"),
        pytest.param("https://zq-public.example.com:8443/folio/", "https://zq-public.example.com:8443/folio", id="path-prefix"),
    ],
)
def test_an_email_link_is_the_base_the_page_and_the_token_in_the_fragment(monkeypatch: pytest.MonkeyPatch, purpose: AccountTokenPurpose, page: str, value: str, base: str) -> None:
    """EML-007 — contract 4: ``email_link`` is exactly ``<base><page>#token=<token>``: the path prefix of the base kept, the token in the fragment and nowhere else."""
    print_section(f"EML-007: {purpose.value} link on {value}")
    _public_url(monkeypatch, value)

    link = email_link(purpose, TOKEN)

    assert link == f"{base}{page}#token={TOKEN}", link
    parts = urlsplit(link)
    assert (parts.query, parse_qs(parts.fragment)) == ("", {"token": [TOKEN]}), f"the token goes in the fragment only: {parts}"
    print_success(link)


def test_a_token_is_urlencoded_in_the_fragment_and_reads_back(monkeypatch: pytest.MonkeyPatch) -> None:
    """EML-008 — contract 4: a token with ``+ / = & space # ? %`` is encoded in the fragment — none of them raw after ``#token=`` — and the fragment parses back to the very token."""
    print_section("EML-008: an awkward token")
    _public_url(monkeypatch, PUBLIC_URL)

    link = email_link(AccountTokenPurpose.PASSWORD_RESET, AWKWARD_TOKEN)

    prefix = f"{PUBLIC_URL}/reset-password#token="
    assert link.startswith(prefix), link
    encoded = link.removeprefix(prefix)
    raw = [char for char in "/=& #?" if char in encoded]
    assert raw == [], f"characters left raw in the encoded token {encoded!r}: {raw}"
    assert parse_qs(urlsplit(link).fragment) == {"token": [AWKWARD_TOKEN]}, f"the fragment does not read back as the token: {link}"
    print_success(link)


@pytest.mark.parametrize(
    ("value", "problem"),
    [
        pytest.param(None, "PUBLIC_URL_MISSING", id="missing"),
        pytest.param("ftp://folio.zq-public.example.com", "PUBLIC_URL_INVALID", id="invalid"),
    ],
)
def test_no_email_link_without_a_usable_public_url(monkeypatch: pytest.MonkeyPatch, value: str | None, problem: str) -> None:
    """EML-009 — contract 4: without a usable base, ``email_link`` raises ``EmailLinksUnavailableError`` with the problem: no link is ever built from anything else."""
    print_section(f"EML-009: email_link, {problem}")
    _public_url(monkeypatch, value)

    with pytest.raises(EmailLinksUnavailableError) as raised:
        email_link(AccountTokenPurpose.PASSWORD_RESET, TOKEN)

    assert raised.value.code == problem
    print_success(problem)


# =============================================================================
# 5. email_instance_config
# =============================================================================


@pytest.mark.parametrize(
    ("smtp", "public_url", "expected"),
    [
        pytest.param({}, None, (False, False), id="email-off-links-missing"),
        pytest.param({}, PUBLIC_URL, (False, False), id="email-off-links-ready"),
        pytest.param(USABLE_SMTP, None, (True, False), id="email-ready-links-missing"),
        pytest.param(USABLE_SMTP, "ftp://folio.zq-public.example.com", (True, False), id="email-ready-links-invalid"),
        pytest.param(USABLE_SMTP, "https://folio.zq-space.example.com/my folio", (True, False), id="email-ready-links-no-link-can-start-from-it"),
        pytest.param(USABLE_SMTP, PUBLIC_URL, (True, True), id="email-ready-links-ready"),
        pytest.param({**USABLE_SMTP, "LIBREFOLIO_SMTP_TLS": "ssl"}, PUBLIC_URL, (False, False), id="email-invalid-links-ready"),
        pytest.param({**USABLE_SMTP, BLOCKED_VARIABLE: "1"}, PUBLIC_URL, (False, False), id="email-and-links-ready-but-blocked"),
        pytest.param({**USABLE_SMTP, BLOCKED_VARIABLE: "maybe"}, PUBLIC_URL, (False, False), id="email-and-links-ready-block-unreadable"),
        pytest.param({**USABLE_SMTP, BLOCKED_VARIABLE: "off"}, PUBLIC_URL, (True, True), id="email-and-links-ready-not-blocked"),
    ],
)
def test_email_instance_config_says_whether_email_and_its_links_work(monkeypatch: pytest.MonkeyPatch, smtp: dict[str, str], public_url: str | None, expected: tuple[bool, bool]) -> None:
    """EML-010 — contract 5: ``available`` is whether email can be used and the instance is not blocked (``LIBREFOLIO_BLOCKED`` blocking, or unreadable: a blocked instance sends nothing); ``links`` is ``available`` and links ready — never true without email, never true without a usable ``LIBREFOLIO_PUBLIC_URL``, never true on a blocked instance. Exactly those two fields."""
    print_section(f"EML-010: email {'usable' if expected[0] else 'not usable'}, LIBREFOLIO_PUBLIC_URL={public_url!r}")
    for name, value in smtp.items():
        monkeypatch.setenv(name, value)
    _public_url(monkeypatch, public_url)

    config = email_instance_config()

    assert isinstance(config, EmailInstanceConfig)
    assert config.model_dump() == {"available": expected[0], "links": expected[1]}, config
    print_success(f"{config.model_dump()}")


# =============================================================================
# 1 and 4. AN HTTP(S) ADDRESS NO LINK CAN START FROM
# =============================================================================


@pytest.mark.parametrize("value", MALFORMED_VALUES)
def test_an_http_address_no_link_can_start_from_is_invalid_and_never_echoed(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    """EML-011 — contract 1: an http(s) address without a host, with a space or a tab inside, with a ``?`` or a ``#`` (even with nothing after it, which would swallow the page's path), with a port out of range or not a number, or with credentials passes the scheme check but cannot start an emailed link: ``PUBLIC_URL_INVALID``, no base, not ready, no instance; ``links_state()`` does not raise and its state does not carry the value."""
    print_section(f"EML-011: LIBREFOLIO_PUBLIC_URL={value!r}")
    _public_url(monkeypatch, value)

    state = links_state()

    assert (state.base, state.problem, state.ready, state.instance) == (None, "PUBLIC_URL_INVALID", False, ""), state
    assert "zq-" not in repr(state), f"the state echoes the invalid value: {state!r}"
    print_success("invalid, not echoed")


@pytest.mark.parametrize("purpose", [AccountTokenPurpose.PASSWORD_RESET, AccountTokenPurpose.INVITE], ids=["password-reset", "invite"])
@pytest.mark.parametrize("value", MALFORMED_VALUES)
def test_no_link_and_no_bare_value_error_from_an_address_no_link_can_start_from(monkeypatch: pytest.MonkeyPatch, purpose: AccountTokenPurpose, value: str) -> None:
    """EML-012 — contracts 3 and 4: on such an address ``require_links()`` and ``email_link()`` raise ``EmailLinksUnavailableError`` itself with ``PUBLIC_URL_INVALID`` — not a bare ``ValueError`` that the message builders would raise on a link with a space, and that a caller would take for a bad recipient —; no link is built."""
    print_section(f"EML-012: {purpose.value} link on {value!r}")
    _public_url(monkeypatch, value)

    with pytest.raises(EmailLinksUnavailableError) as required:
        require_links()
    with pytest.raises(EmailError) as linked:
        email_link(purpose, TOKEN)

    assert required.value.code == "PUBLIC_URL_INVALID", required.value
    assert type(linked.value) is EmailLinksUnavailableError and linked.value.code == "PUBLIC_URL_INVALID", repr(linked.value)
    print_success("EmailLinksUnavailableError PUBLIC_URL_INVALID, no link")
