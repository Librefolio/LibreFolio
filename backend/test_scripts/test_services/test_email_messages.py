"""``backend.app.services.email.messages``: what LibreFolio writes in an e-mail, in four languages (plan phase01Email §3.2, decision D-E8, lot E1).

Every e-mail of release 1.3 — password reset, invitation, e-mail verification, activation of the first administrator,
test message — is built by one typed builder from the texts of ``templates/{en,it,fr,es}.json`` and the HTML layout
``templates/layout.html``, then composed into a ``multipart/alternative`` message. The contract pinned here:

1. ``EMAIL_LANGUAGES`` are the four languages ``default_language`` accepts; ``EmailKind`` has six values (lot E4a adds
   ``email_changed``);
   ``email_language`` reduces any language tag to one of them (``it-IT``, ``IT``, ``it_IT`` → ``it``), English when it
   is unknown, empty or missing.
2. ``EmailContent(kind, language, subject, text, html)`` is frozen.
3. One keyword-only builder per kind; the language goes through ``email_language``; a link must start with
   ``http://`` or ``https://`` — ``javascript:``, ``data:``, a relative path is a ``ValueError``.
4. Rendering: the link verbatim in the text and, escaped, as an ``href`` in the HTML; the username — in the two kinds
   that still show one, ``admin_setup`` and ``test`` (contract 9) —, the instance and the inviter in both parts and
   escaped in the HTML, so markup in a username never becomes markup; none of them and no link in the subject; the
   validity written by Babel, ``format_timedelta(ttl, locale=language)``, in both parts; an invitation that grants
   administrator rights says so in one more sentence; the inviter named when known, and only then; the HTML declares
   its ``lang``; no part empty, no ``$placeholder`` left behind.
5. The catalogue: the four JSON files and ``layout.html`` exist; the JSON files parse, have exactly the same nested
   keys, non-empty strings only, the same ``$placeholders`` for each key in every language and valid
   ``string.Template`` syntax — a translation can neither lose a value nor break the rendering.
6. ``compose_message``: ``Subject``, ``From``, ``To``, ``Reply-To`` only when given, ``Date`` (``now`` when given), a
   ``Message-ID`` in the sender's domain, ``Content-Language``, ``Auto-Submitted: auto-generated``,
   ``X-Auto-Response-Suppress: All``, each once; a ``multipart/alternative`` body, plain text first and HTML last (the
   last alternative is the one a client prefers); exactly one recipient address — a CR or LF, a comma, no ``@`` or
   whitespace inside is a ``ValueError``; a non-ASCII display name still makes an ASCII (RFC 2047) header.
7. Every value an e-mail shows — the username, the instance, the inviter — goes in as one line of plain text (lot E3,
   security review): a control character (Cc: a line feed, a carriage return, a tab, NUL…) or a line or paragraph
   separator (Zl, Zp) becomes one space, so the plain-text part keeps its lines whatever a value holds; a bidirectional
   embedding, override or isolate (U+202A–U+202E, U+2066–U+2069) is removed, so a value cannot reorder the text around
   it; the HTML part is escaped as before.
8. The notice of an email change (lot E4a, then decision N62): the sections of every catalogue are exactly the kinds of
   ``EmailKind`` and ``common``; ``build_email_changed(*, language, instance)`` writes, in each language, the anonymous
   greeting, the intro naming ``$instance`` alone, the advice naming ``$instance``, then the footer — and nothing else:
   no link, no button, no ``href`` at all. It cannot receive the new address, so no part of it — neither its local part
   nor its domain, nor any mask of it — is in its subject, its text or its HTML: a domain is a host name its new owner
   chose freely, which mail clients make a link. ``masked_address``, whose only use was the notice, no longer exists
   (the delivery masks an address an SMTP server quotes in its own way, ``delivery._redacted``, pinned in
   ``test_email_delivery.py``).
9. No email an untrusted party can address carries text they chose (decision N62, E-9 b and c):
   ``build_password_reset(*, language, link, ttl, instance)``, ``build_verification(*, language, link, ttl,
   instance)`` and ``build_email_changed(*, language, instance)`` take no ``username`` — a crafted one, with markup, a
   link to a site of its writer's, a CR LF, cannot even be passed: a ``TypeError`` — and open with
   ``common.greeting_anonymous`` («Hello,», «Ciao,», «Bonjour,», «Hola:»), as the invitation does; no text of those
   three sections holds ``$username``, and ``email_changed.intro`` holds ``$instance`` and no ``$address``.
   ``build_admin_setup`` and ``build_test_message`` keep ``username`` and ``common.greeting``: their sender is trusted,
   the operator, or an administrator writing to themselves.

Pure: no database, no server, no network; the catalogue is read from the package, never written. The autouse fixture
that removes inherited ``LIBREFOLIO_SMTP_*`` variables is here as in every module of the e-mail lot, though nothing
here reads them.

Red until ``backend/app/services/email/messages.py`` exists: the package does not import.
"""

from __future__ import annotations

import collections
import dataclasses
import html
import inspect
import json
import os
import re
import string
from datetime import UTC, datetime, timedelta
from email import policy
from email.message import EmailMessage
from email.parser import BytesParser
from enum import StrEnum
from pathlib import Path

import pytest
from babel.dates import format_timedelta

from backend.app.schemas.settings import GLOBAL_SETTINGS_CONSTRAINTS
from backend.app.services.email import messages
from backend.app.services.email.messages import (
    EMAIL_LANGUAGES,
    EmailContent,
    EmailKind,
    build_admin_setup,
    build_email_changed,
    build_invite,
    build_password_reset,
    build_test_message,
    build_verification,
    compose_message,
    email_language,
)
from backend.test_scripts.test_utils import print_section, print_success

SMTP_PREFIX = "LIBREFOLIO_SMTP_"
LANGUAGES = ("en", "it", "fr", "es")
TEMPLATES = Path(messages.__file__).parent / "templates"

TOKEN = "Zm9v_YmFy-0123456789abcdefghijklmnopqrstuv"
#: A link with an ``&``: its escaping in the HTML is visible.
LINK = f"https://folio.example.com/reset-password?source=email&lang=it#token={TOKEN}"
#: Plain HTTP is a link too: an instance on a home network.
HTTP_LINK = "http://192.168.1.10:6040/invite#token=bGFu_aW52aXRl"
#: The user's values carry markup and quotes: escaped in the HTML, they cannot become markup.
USERNAME = '<b>zq-alice</b>&"'
INSTANCE = "Zq Family <Folio> & Co"
INVITER = "zq-O'Brien <admin>"
#: The new address of an email change: a local part and a domain its new owner chose, neither of which the notice shows.
NEW_ADDRESS = "zq.new-alice.secret@Example.ORG"
NEW_LOCAL_PART = "zq.new-alice.secret"
NEW_DOMAIN = "Example.ORG"
#: What may never reach a subject, in any case: the cores of the user's values, and any trace of the link.
NOT_IN_A_SUBJECT = ("zq-alice", "zq family", "brien", "://", "folio.example.com", TOKEN.lower(), "example.org")

PASSWORD_RESET, INVITE, EMAIL_VERIFICATION, ADMIN_SETUP, TEST, EMAIL_CHANGED = (
    EmailKind.PASSWORD_RESET,
    EmailKind.INVITE,
    EmailKind.EMAIL_VERIFICATION,
    EmailKind.ADMIN_SETUP,
    EmailKind.TEST,
    EmailKind.EMAIL_CHANGED,
)
ALL_KINDS = (PASSWORD_RESET, INVITE, EMAIL_VERIFICATION, ADMIN_SETUP, TEST, EMAIL_CHANGED)
LINK_KINDS = (PASSWORD_RESET, INVITE, EMAIL_VERIFICATION, ADMIN_SETUP)
TTL = {PASSWORD_RESET: timedelta(minutes=30), INVITE: timedelta(days=7), EMAIL_VERIFICATION: timedelta(hours=24), ADMIN_SETUP: timedelta(hours=72)}

#: Each builder with the arguments this module gives it, the language aside: exactly the keywords it takes. The three
#: kinds an untrusted party can address take no username, and the notice no new address (decision N62, contract 9).
BUILDERS = {
    PASSWORD_RESET: (build_password_reset, {"link": LINK, "ttl": TTL[PASSWORD_RESET], "instance": INSTANCE}),
    INVITE: (build_invite, {"link": LINK, "ttl": TTL[INVITE], "instance": INSTANCE, "inviter": INVITER}),
    EMAIL_VERIFICATION: (build_verification, {"link": LINK, "ttl": TTL[EMAIL_VERIFICATION], "instance": INSTANCE}),
    ADMIN_SETUP: (build_admin_setup, {"username": USERNAME, "link": LINK, "ttl": TTL[ADMIN_SETUP], "instance": INSTANCE}),
    TEST: (build_test_message, {"username": USERNAME, "instance": INSTANCE}),
    EMAIL_CHANGED: (build_email_changed, {"instance": INSTANCE}),
}
#: The user's values each kind shows.
SHOWN_VALUES = {
    PASSWORD_RESET: (INSTANCE,),
    INVITE: (INSTANCE, INVITER),
    EMAIL_VERIFICATION: (INSTANCE,),
    ADMIN_SETUP: (USERNAME, INSTANCE),
    TEST: (USERNAME, INSTANCE),
    EMAIL_CHANGED: (INSTANCE,),
}
#: The parameters of each builder, all keyword-only, and the defaults of the optional ones.
SIGNATURES = {
    "build_password_reset": ({"language", "link", "ttl", "instance"}, {}),
    "build_invite": ({"language", "link", "ttl", "instance", "inviter", "grants_admin"}, {"inviter": None, "grants_admin": False}),
    "build_verification": ({"language", "link", "ttl", "instance"}, {}),
    "build_admin_setup": ({"language", "username", "link", "ttl", "instance"}, {}),
    "build_test_message": ({"language", "username", "instance"}, {}),
    "build_email_changed": ({"language", "instance"}, {}),
}
#: The arguments of each builder that an e-mail shows to its reader (the three kinds an untrusted party can address
#: show no username, and the notice no part of the new address: EMM-036 to EMM-041).
SHOWN_FIELDS = {
    PASSWORD_RESET: ("instance",),
    INVITE: ("instance", "inviter"),
    EMAIL_VERIFICATION: ("instance",),
    ADMIN_SETUP: ("username", "instance"),
    TEST: ("username", "instance"),
    EMAIL_CHANGED: ("instance",),
}
SHOWN_FIELD_CASES = [pytest.param(kind, field, id=f"{kind.value}-{field}") for kind, fields in SHOWN_FIELDS.items() for field in fields]
#: Characters that would break a line of the plain-text part, or hide in it: control characters (Cc), the line and
#: paragraph separators (Zl, Zp). In a value, each becomes one space.
LINE_BREAKERS = {
    "LF": "\n",
    "CRLF": "\r\n",
    "CR": "\r",
    "VT": "\x0b",
    "FF": "\x0c",
    "FS": "\x1c",
    "NEL": "\x85",
    "LINE SEPARATOR": "\u2028",
    "PARAGRAPH SEPARATOR": "\u2029",
    "TAB": "\t",
    "ESC": "\x1b",
    "NUL": "\x00",
}
#: The ones no template writes itself: none of them may be left anywhere in an e-mail built from a value holding it.
FOREIGN_BREAKERS = ("VT", "FF", "FS", "NEL", "LINE SEPARATOR", "PARAGRAPH SEPARATOR", "ESC", "NUL")
#: The bidirectional embeddings, overrides and isolates: in a value, removed.
BIDI_CONTROLS = "\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069"

SENDER = ("LibreFolio", "noreply@example.com")
REPLY_TO = ("LibreFolio Support", "support@example.org")
RECIPIENT = "alice@example.com"
NOW = datetime(2026, 10, 15, 9, 30, 0, tzinfo=UTC)
#: Content built by hand, so that ``compose_message`` is tested apart from the builders.
CONTENT = EmailContent(
    kind=TEST,
    language="it",
    subject="Prova di invio",
    text="Ciao,\nquesta è un'email di prova.\n",
    html='<!DOCTYPE html>\n<html lang="it"><body><p>Ciao, questa è un&#x27;email di prova.</p></body></html>\n',
)

_PLACEHOLDER = re.compile(r"\$(?:[_A-Za-z]|\{)")
_SENTENCE_BREAK = re.compile(r"(?<=[.!?…])\s+|\n+")
_HREF = re.compile(r"""\bhref\s*=\s*(["'])(.*?)\1""", re.IGNORECASE | re.DOTALL)


@pytest.fixture(autouse=True)
def _no_inherited_smtp_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every ``LIBREFOLIO_SMTP_*`` the lane inherited is removed: no e-mail test ever reads the lane's configuration."""
    for name in list(os.environ):
        if name.startswith(SMTP_PREFIX):
            monkeypatch.delenv(name, raising=False)


def _build(kind: EmailKind, language: str | None = "en", **overrides: object) -> EmailContent:
    """The e-mail of ``kind`` with this module's values — exactly the keywords its builder takes (BUILDERS) —, ``overrides`` replacing some of them."""
    builder, arguments = BUILDERS[kind]
    return builder(**{"language": language, **arguments, **overrides})


def _hrefs(document: str) -> list[str]:
    """Every ``href`` of ``document``, unescaped: what a mail client opens."""
    return [html.unescape(value) for _, value in _HREF.findall(document)]


def _sentences(text: str) -> collections.Counter[str]:
    """The sentences and lines of ``text``, counted: a sentence ends with ``.``, ``!``, ``?`` or ``…`` before a space, a line with its break."""
    return collections.Counter(part.strip() for part in _SENTENCE_BREAK.split(text) if part.strip())


def _catalogue(language: str) -> object:
    return json.loads((TEMPLATES / f"{language}.json").read_text(encoding="utf-8"))


def _leaves(node: object, path: str = "") -> dict[str, object]:
    """Every leaf of a nested JSON object by its dotted path."""
    if not isinstance(node, dict):
        return {path: node}
    leaves: dict[str, object] = {}
    for key, value in node.items():
        leaves.update(_leaves(value, f"{path}.{key}" if path else str(key)))
    return leaves


def _parsed(message: EmailMessage) -> EmailMessage:
    """``message`` as a mail server receives it: serialized, then parsed back."""
    return BytesParser(policy=policy.default).parsebytes(message.as_bytes())


def _mailboxes(header: object) -> list[tuple[str, str]]:
    return [(address.display_name, address.addr_spec) for address in header.addresses]


def _lines(text: str) -> str:
    """``text`` without the line-ending differences a MIME round trip brings: CRLF as LF, no trailing line break."""
    return text.replace("\r\n", "\n").rstrip("\n")


# =============================================================================
# 1. LANGUAGES AND KINDS
# =============================================================================


def test_the_email_languages_are_those_of_default_language() -> None:
    """EMM-001 — contract 1: English, Italian, French, Spanish — the very choices of the ``default_language`` setting, so that no account can pick a language its e-mails lack."""
    print_section("EMM-001: EMAIL_LANGUAGES")

    assert EMAIL_LANGUAGES == LANGUAGES
    assert tuple(EMAIL_LANGUAGES) == tuple(GLOBAL_SETTINGS_CONSTRAINTS["default_language"].choices)
    print_success("en, it, fr, es = default_language choices")


def test_the_kinds_of_email_have_their_values() -> None:
    """EMM-002 — contract 1: six kinds, a StrEnum of lowercase values (``email_changed`` since lot E4a)."""
    print_section("EMM-002: EmailKind")

    assert issubclass(EmailKind, StrEnum)
    assert {kind.name: kind.value for kind in EmailKind} == {
        "PASSWORD_RESET": "password_reset",
        "INVITE": "invite",
        "EMAIL_VERIFICATION": "email_verification",
        "ADMIN_SETUP": "admin_setup",
        "TEST": "test",
        "EMAIL_CHANGED": "email_changed",
    }
    print_success("6 kinds")


@pytest.mark.parametrize(
    ("language", "expected"),
    [
        ("en", "en"),
        ("it", "it"),
        ("fr", "fr"),
        ("es", "es"),
        ("it-IT", "it"),
        ("IT", "it"),
        ("it_IT", "it"),
        ("fr-CA", "fr"),
        ("ES", "es"),
        ("en-GB", "en"),
        ("de", "en"),
        ("de-DE", "en"),
        ("pt_BR", "en"),
        ("", "en"),
        ("   ", "en"),
        (None, "en"),
    ],
)
def test_email_language_reduces_a_tag_to_a_supported_language(language: str | None, expected: str) -> None:
    """EMM-003 — contract 1: lowercased, region dropped; an unknown, empty or missing language is English."""
    print_section(f"EMM-003: email_language({language!r})")

    assert email_language(language) == expected
    print_success(f"→ {expected}")


# =============================================================================
# 2-3. CONTENT AND BUILDERS
# =============================================================================


def test_email_content_is_a_frozen_dataclass() -> None:
    """EMM-004 — contract 2: kind, language, subject, text, html — in that order, never edited after the build."""
    print_section("EMM-004: EmailContent")

    assert [field.name for field in dataclasses.fields(EmailContent)] == ["kind", "language", "subject", "text", "html"]
    with pytest.raises(dataclasses.FrozenInstanceError):
        CONTENT.subject = "changed"  # type: ignore[misc]
    print_success("frozen, five fields")


@pytest.mark.parametrize("name", list(SIGNATURES))
def test_each_builder_takes_keyword_arguments_only(name: str) -> None:
    """EMM-005 — contract 3: the parameters of the contract, every one keyword-only; only ``build_invite`` has defaults, ``inviter=None`` and ``grants_admin=False``. ``build_password_reset``, ``build_verification`` and ``build_email_changed`` take no ``username``, and the last no ``new_address`` either (contract 9)."""
    print_section(f"EMM-005: {name}")
    names, defaults = SIGNATURES[name]

    parameters = inspect.signature(getattr(messages, name)).parameters

    assert set(parameters) == names
    assert all(parameter.kind is inspect.Parameter.KEYWORD_ONLY for parameter in parameters.values())
    assert {key: parameter.default for key, parameter in parameters.items() if parameter.default is not inspect.Parameter.empty} == defaults
    print_success("keyword-only")


@pytest.mark.parametrize(("language", "expected"), [("en", "en"), ("it", "it"), ("fr-FR", "fr"), ("ES", "es"), ("de", "en"), (None, "en")])
@pytest.mark.parametrize("kind", ALL_KINDS, ids=str)
def test_each_builder_makes_its_kind_in_a_supported_language(kind: EmailKind, language: str | None, expected: str) -> None:
    """EMM-006 — contract 3: an ``EmailContent`` of the builder's kind, its language passed through ``email_language``."""
    print_section(f"EMM-006: {kind} in {language!r}")

    content = _build(kind, language)

    assert isinstance(content, EmailContent)
    assert (content.kind, content.language) == (kind, expected)
    print_success(f"{kind}, {expected}")


@pytest.mark.parametrize(
    "link",
    [
        "javascript:alert(1)",
        "data:text/html;base64,PHNjcmlwdD4=",
        "mailto:alice@example.com",
        "ftp://folio.example.com/reset-password",
        "/reset-password#token=abc",
        "folio.example.com/reset-password",
        "",
    ],
)
@pytest.mark.parametrize("kind", LINK_KINDS, ids=str)
def test_a_link_that_is_not_http_is_refused(kind: EmailKind, link: str) -> None:
    """EMM-007 — contract 3: only ``http://`` and ``https://`` links go into an e-mail; anything else is a ``ValueError``, not a message."""
    print_section(f"EMM-007: {kind} with {link!r}")

    with pytest.raises(ValueError):
        _build(kind, "en", link=link)
    print_success("ValueError")


# =============================================================================
# 4. RENDERING
# =============================================================================


@pytest.mark.parametrize("language", LANGUAGES)
@pytest.mark.parametrize("kind", LINK_KINDS, ids=str)
def test_the_link_is_verbatim_in_the_text_and_escaped_in_an_href(kind: EmailKind, language: str) -> None:
    """EMM-008 — contract 4: the text holds the link character for character; the HTML holds it as an ``href`` that unescapes to it, and never raw — its ``&`` is escaped."""
    print_section(f"EMM-008: the link of {kind} in {language}")

    content = _build(kind, language)

    assert LINK in content.text
    assert LINK in _hrefs(content.html), f"no href opens the link: {_hrefs(content.html)}"
    assert LINK not in content.html, "the link reached the HTML unescaped"
    print_success("verbatim in the text, escaped in an href")


@pytest.mark.parametrize("kind", LINK_KINDS, ids=str)
def test_a_plain_http_link_is_a_link(kind: EmailKind) -> None:
    """EMM-009 — contract 3: an instance on a home network has an ``http://`` link, and it is used as given."""
    print_section(f"EMM-009: {kind} with an http link")

    content = _build(kind, "en", link=HTTP_LINK)

    assert HTTP_LINK in content.text
    assert HTTP_LINK in _hrefs(content.html)
    print_success("http accepted")


@pytest.mark.parametrize("language", LANGUAGES)
@pytest.mark.parametrize("kind", ALL_KINDS, ids=str)
def test_the_users_values_are_in_both_parts_and_escaped_in_the_html(kind: EmailKind, language: str) -> None:
    """EMM-010 — contract 4: the values each kind shows — the username (``admin_setup`` and ``test`` alone), the instance, the inviter — appear in the text as written and in the HTML escaped — a username ``<b>…</b>&"`` never appears raw there."""
    print_section(f"EMM-010: values of {kind} in {language}")

    content = _build(kind, language)

    for value in SHOWN_VALUES[kind]:
        assert value in content.text, f"{value!r} is not in the text"
        assert value not in content.html, f"{value!r} reached the HTML unescaped"
        assert value in html.unescape(content.html), f"{value!r} is not in the HTML"
    print_success("in both parts, escaped in the HTML")


@pytest.mark.parametrize("language", LANGUAGES)
@pytest.mark.parametrize("kind", ALL_KINDS, ids=str)
def test_the_subject_holds_no_user_value_and_no_link(kind: EmailKind, language: str) -> None:
    """EMM-011 — contract 4: a subject is seen by every relay and every notification: no username, inviter or instance, and no link."""
    print_section(f"EMM-011: subject of {kind} in {language}")

    subject = _build(kind, language).subject.lower()

    assert [marker for marker in NOT_IN_A_SUBJECT if marker in subject] == []
    print_success(repr(subject))


@pytest.mark.parametrize("language", LANGUAGES)
@pytest.mark.parametrize("kind", LINK_KINDS, ids=str)
def test_the_validity_is_written_by_babel(kind: EmailKind, language: str) -> None:
    """EMM-012 — contract 4: how long the link lasts is ``format_timedelta(ttl, locale=language)``, in both parts."""
    print_section(f"EMM-012: validity of {kind} in {language}")

    content = _build(kind, language)
    expected = format_timedelta(TTL[kind], locale=language)

    assert expected in content.text, f"{expected!r} is not in the text"
    assert expected in html.unescape(content.html), f"{expected!r} is not in the HTML"
    print_success(expected)


@pytest.mark.parametrize(
    ("kind", "language", "ttl", "expected"),
    [
        (PASSWORD_RESET, "it", timedelta(minutes=30), "30 minuti"),
        (PASSWORD_RESET, "en", timedelta(hours=2), "2 hours"),
        (INVITE, "en", timedelta(days=7), "1 week"),
        (INVITE, "it", timedelta(days=7), "1 settimana"),
        (EMAIL_VERIFICATION, "it", timedelta(hours=24), "1 giorno"),
        (ADMIN_SETUP, "it", timedelta(hours=72), "3 giorni"),
    ],
)
def test_the_validity_reads_naturally(kind: EmailKind, language: str, ttl: timedelta, expected: str) -> None:
    """EMM-013 — contract 4: Babel's default wording, pinned on a few cases — and the ``ttl`` given is the one written, not the purpose's default."""
    print_section(f"EMM-013: {ttl} in {language}")

    content = _build(kind, language, ttl=ttl)

    assert expected in content.text
    assert expected in html.unescape(content.html)
    print_success(expected)


@pytest.mark.parametrize("language", LANGUAGES)
def test_an_invitation_granting_admin_rights_says_so_in_one_more_sentence(language: str) -> None:
    """EMM-014 — contract 4: the text of an invitation with ``grants_admin=True`` is the text without it plus exactly one sentence; the HTML differs too."""
    print_section(f"EMM-014: admin invitation in {language}")

    plain = _build(INVITE, language, grants_admin=False)
    admin = _build(INVITE, language, grants_admin=True)
    added = _sentences(admin.text) - _sentences(plain.text)
    removed = _sentences(plain.text) - _sentences(admin.text)

    assert sum(added.values()) == 1, f"sentences added for admin rights: {list(added)}"
    assert not removed, f"sentences of the invitation missing once it grants admin rights: {list(removed)}"
    assert admin.html != plain.html
    print_success(f"one more sentence: {next(iter(added))!r}")


@pytest.mark.parametrize("language", LANGUAGES)
def test_the_inviter_is_named_when_known_and_only_then(language: str) -> None:
    """EMM-015 — contract 4: with an inviter the invitation names them in both parts; without one it names nobody — no ``None``, no placeholder."""
    print_section(f"EMM-015: inviter in {language}")

    named = _build(INVITE, language, inviter=INVITER)
    anonymous = _build(INVITE, language, inviter=None)

    assert INVITER in named.text and INVITER in html.unescape(named.html)
    for part in (anonymous.subject, anonymous.text, html.unescape(anonymous.html)):
        assert "brien" not in part.lower()
        assert not re.search(r"\bNone\b", part), "an absent inviter was written as None"
        assert not _PLACEHOLDER.search(part), "an absent inviter left its placeholder"
    print_success("named when known, absent otherwise")


@pytest.mark.parametrize("language", LANGUAGES)
@pytest.mark.parametrize("kind", ALL_KINDS, ids=str)
def test_the_html_declares_its_language(kind: EmailKind, language: str) -> None:
    """EMM-016 — contract 4: ``<html lang="…">`` in the language of the content, for screen readers and spell checkers."""
    print_section(f"EMM-016: lang of {kind} in {language}")

    content = _build(kind, language)

    assert re.search(rf"""<html\b[^>]*\blang\s*=\s*(["']){language}\1""", content.html, flags=re.IGNORECASE), "the <html> element does not declare its lang"
    print_success(f'lang="{language}"')


@pytest.mark.parametrize("language", LANGUAGES)
@pytest.mark.parametrize("kind", ALL_KINDS, ids=str)
def test_no_part_is_empty_and_no_placeholder_is_left(kind: EmailKind, language: str) -> None:
    """EMM-017 — contract 4: subject, text and HTML all have content, none keeps a ``$placeholder``, and the subject is one line."""
    print_section(f"EMM-017: parts of {kind} in {language}")

    content = _build(kind, language)

    for name, part in (("subject", content.subject), ("text", content.text), ("html", content.html)):
        assert part.strip(), f"the {name} is empty"
        assert not _PLACEHOLDER.search(part), f"the {name} keeps a placeholder: {_PLACEHOLDER.search(part)}"
    assert "\n" not in content.subject and "\r" not in content.subject
    print_success("three parts, all rendered")


# =============================================================================
# 5. THE CATALOGUE
# =============================================================================


def test_the_catalogue_files_exist() -> None:
    """EMM-018 — contract 5: ``templates/`` beside ``messages.py`` holds a JSON file per language and the HTML layout."""
    print_section("EMM-018: catalogue files")

    missing = [name for name in (*(f"{language}.json" for language in LANGUAGES), "layout.html") if not (TEMPLATES / name).is_file()]

    assert missing == [], f"missing in {TEMPLATES}: {missing}"
    print_success(f"{len(LANGUAGES)} catalogues and layout.html")


@pytest.mark.parametrize("language", LANGUAGES)
def test_each_catalogue_is_a_json_object(language: str) -> None:
    """EMM-019 — contract 5: each file parses as UTF-8 JSON, and its root is a non-empty object."""
    print_section(f"EMM-019: {language}.json parses")

    catalogue = _catalogue(language)

    assert isinstance(catalogue, dict) and catalogue
    print_success(f"{len(_leaves(catalogue))} texts")


@pytest.mark.parametrize("language", [language for language in LANGUAGES if language != "en"])
def test_every_catalogue_has_the_keys_of_the_english_one(language: str) -> None:
    """EMM-020 — contract 5: exactly the same nested keys as English: a text missing in one language is a gap, an extra one is dead."""
    print_section(f"EMM-020: keys of {language}.json")

    english, other = set(_leaves(_catalogue("en"))), set(_leaves(_catalogue(language)))

    assert sorted(english - other) == [], f"missing in {language}.json"
    assert sorted(other - english) == [], f"only in {language}.json"
    print_success(f"{len(english)} keys, the same")


@pytest.mark.parametrize("language", LANGUAGES)
def test_every_text_is_a_non_empty_string(language: str) -> None:
    """EMM-021 — contract 5: every leaf is a string with something in it — no number, list, null or blank."""
    print_section(f"EMM-021: values of {language}.json")

    bad = {path: value for path, value in _leaves(_catalogue(language)).items() if not isinstance(value, str) or not value.strip()}

    assert bad == {}
    print_success("strings only, none blank")


@pytest.mark.parametrize("language", [language for language in LANGUAGES if language != "en"])
def test_every_text_has_the_placeholders_of_its_english_original(language: str) -> None:
    """EMM-022 — contract 5: for each key, the ``string.Template`` identifiers are the same set as in English: a translation neither drops the link nor invents a value."""
    print_section(f"EMM-022: placeholders of {language}.json")
    english, other = _leaves(_catalogue("en")), _leaves(_catalogue(language))

    different = {
        path: (sorted(string.Template(english[path]).get_identifiers()), sorted(string.Template(other[path]).get_identifiers()))
        for path in sorted(set(english) & set(other))
        if isinstance(english[path], str) and isinstance(other[path], str) and set(string.Template(english[path]).get_identifiers()) != set(string.Template(other[path]).get_identifiers())
    }

    assert different == {}, f"(en, {language}) placeholders differ"
    print_success("same placeholders, key by key")


@pytest.mark.parametrize("language", LANGUAGES)
def test_every_text_is_a_valid_template(language: str) -> None:
    """EMM-023 — contract 5: no stray ``$`` — every text is valid ``string.Template`` syntax, so rendering cannot fail on a translation."""
    print_section(f"EMM-023: template syntax of {language}.json")

    invalid = [path for path, value in _leaves(_catalogue(language)).items() if isinstance(value, str) and not string.Template(value).is_valid()]

    assert invalid == []
    print_success("valid templates")


# =============================================================================
# 6. COMPOSITION
# =============================================================================


def test_compose_message_takes_the_content_then_keywords() -> None:
    """EMM-024 — contract 6: ``compose_message(content, *, to, sender, reply_to=None, now=None)``."""
    print_section("EMM-024: compose_message signature")

    parameters = inspect.signature(compose_message).parameters

    assert list(parameters)[0] == "content" and set(parameters) == {"content", "to", "sender", "reply_to", "now"}
    assert all(parameters[key].kind is inspect.Parameter.KEYWORD_ONLY for key in ("to", "sender", "reply_to", "now"))
    assert (parameters["reply_to"].default, parameters["now"].default) == (None, None)
    print_success("content, then keywords")


def test_compose_message_writes_every_header_once_and_both_alternatives() -> None:
    """EMM-025 — contract 6: the headers of the contract, each once, as a server parses them; the body ``multipart/alternative`` with the text first and the HTML last, equal to the content's parts once line endings are normalized."""
    print_section("EMM-025: compose_message")

    message = compose_message(CONTENT, to=RECIPIENT, sender=SENDER, reply_to=REPLY_TO, now=NOW)

    assert isinstance(message, EmailMessage)
    parsed = _parsed(message)
    headers = ("Subject", "From", "To", "Reply-To", "Date", "Message-ID", "Content-Language", "Auto-Submitted", "X-Auto-Response-Suppress")
    assert {name: len(parsed.get_all(name, [])) for name in headers} == dict.fromkeys(headers, 1)
    assert parsed["Subject"] == CONTENT.subject
    assert _mailboxes(parsed["From"]) == [SENDER]
    assert _mailboxes(parsed["To"]) == [("", RECIPIENT)]
    assert _mailboxes(parsed["Reply-To"]) == [REPLY_TO]
    assert parsed["Date"].datetime == NOW
    assert re.fullmatch(r"<[^<>@\s]+@example\.com>", str(parsed["Message-ID"]).strip()), parsed["Message-ID"]
    assert parsed["Content-Language"] == "it"
    assert parsed["Auto-Submitted"] == "auto-generated"
    assert parsed["X-Auto-Response-Suppress"] == "All"
    assert parsed.get_content_type() == "multipart/alternative"
    parts = list(parsed.iter_parts())
    assert [part.get_content_type() for part in parts] == ["text/plain", "text/html"]
    assert _lines(parts[0].get_content()) == _lines(CONTENT.text)
    assert _lines(parts[1].get_content()) == _lines(CONTENT.html)
    print_success("headers once each, text then HTML")


def test_compose_message_writes_no_reply_to_unless_given() -> None:
    """EMM-026 — contract 6: ``Reply-To`` only when there is one."""
    print_section("EMM-026: no Reply-To")

    parsed = _parsed(compose_message(CONTENT, to=RECIPIENT, sender=SENDER, now=NOW))

    assert "Reply-To" not in parsed
    print_success("absent")


def test_compose_message_dates_the_message_now_without_now() -> None:
    """EMM-027 — contract 6: without ``now`` the ``Date`` is the current time, bracketed by two readings, never waited for (a ``-0000`` date is read as UTC)."""
    print_section("EMM-027: Date without now")

    before = datetime.now(UTC).replace(microsecond=0)
    message = compose_message(CONTENT, to=RECIPIENT, sender=SENDER)
    after = datetime.now(UTC)

    date = _parsed(message)["Date"].datetime
    date = date if date.tzinfo is not None else date.replace(tzinfo=UTC)
    assert before <= date <= after, f"{date} outside [{before}, {after}]"
    print_success(date.isoformat())


def test_the_message_id_is_in_the_domain_of_the_sender() -> None:
    """EMM-028 — contract 6: the ``Message-ID`` takes the domain of the sender's address, never the host's name."""
    print_section("EMM-028: Message-ID domain")

    parsed = _parsed(compose_message(CONTENT, to=RECIPIENT, sender=("", "noreply@mail.example.org"), now=NOW))

    assert re.fullmatch(r"<[^<>@\s]+@mail\.example\.org>", str(parsed["Message-ID"]).strip()), parsed["Message-ID"]
    print_success(str(parsed["Message-ID"]))


@pytest.mark.parametrize(
    "to",
    [
        pytest.param("alice@example.com\r\nBcc: eve@example.org", id="crlf-injection"),
        pytest.param("alice@example.com\n", id="lf"),
        pytest.param("alice@example.com\r", id="cr"),
        pytest.param("alice@example.com, bob@example.com", id="comma"),
        pytest.param("alice.example.com", id="no-at"),
        pytest.param("alice @example.com", id="space-before-at"),
        pytest.param("alice@exa mple.com", id="space-in-domain"),
        pytest.param("alice@example.com\tbob@example.com", id="tab"),
    ],
)
def test_compose_message_takes_exactly_one_recipient_address(to: str) -> None:
    """EMM-029 — contract 6: a CR or LF, a comma, no ``@`` or whitespace inside is a ``ValueError``: no message is composed for a second, hidden recipient."""
    print_section(f"EMM-029: to={to!r}")

    with pytest.raises(ValueError):
        compose_message(CONTENT, to=to, sender=SENDER, now=NOW)
    print_success("ValueError")


def test_a_non_ascii_display_name_makes_a_valid_header() -> None:
    """EMM-030 — contract 6: ``Libre Folìo`` as the sender's name: the serialized headers are ASCII (RFC 2047 encoded words), and a server reads the name back."""
    print_section("EMM-030: non-ASCII display name")

    message = compose_message(CONTENT, to=RECIPIENT, sender=("Libre Folìo", "noreply@example.com"), now=NOW)

    head = re.split(rb"\r?\n\r?\n", message.as_bytes(), maxsplit=1)[0]
    assert head.isascii(), "the headers are not ASCII: a server without SMTPUTF8 may refuse them"
    assert _mailboxes(_parsed(message)["From"]) == [("Libre Folìo", "noreply@example.com")]
    print_success("encoded, and read back")


# =============================================================================
# 7. EVERY VALUE ON ONE LINE
# =============================================================================


@pytest.mark.parametrize(("kind", "field"), SHOWN_FIELD_CASES)
def test_a_value_with_a_line_break_stays_on_one_line(kind: EmailKind, field: str) -> None:
    """EMM-031 — contract 7: a value the e-mail shows holding a line break of any kind — LF, CRLF, CR, VT, FF, FS, NEL, U+2028, U+2029 — or another control character — TAB, ESC, NUL —: the plain-text part has exactly as many lines as with a plain value; the value reads with each such character turned into one space, in both parts; and a character no template writes itself is left nowhere."""
    print_section(f"EMM-031: line breaks in the {field} of {kind}")
    plain = _build(kind, **{field: "zq-first zq-second"})
    failures = []
    for name, breaker in LINE_BREAKERS.items():
        content = _build(kind, **{field: f"zq-first{breaker}zq-second"})
        one_line = "zq-first" + " " * len(breaker) + "zq-second"
        if len(content.text.splitlines()) != len(plain.text.splitlines()):
            failures.append(f"{name}: {len(content.text.splitlines())} lines in the text instead of {len(plain.text.splitlines())}")
        if one_line not in content.text or one_line not in content.html:
            failures.append(f"{name}: {one_line!r} missing from the text or the HTML")
        if name in FOREIGN_BREAKERS and (breaker in content.text or breaker in content.html):
            failures.append(f"{name}: left in the e-mail")

    assert failures == [], "\n".join(failures)
    print_success(f"{len(LINE_BREAKERS)} kinds of break, the {field} on one line every time")


@pytest.mark.parametrize(("kind", "field"), SHOWN_FIELD_CASES)
def test_a_value_cannot_reorder_the_text_around_it(kind: EmailKind, field: str) -> None:
    """EMM-032 — contract 7: a value holding a bidirectional embedding, override or isolate (U+202A–U+202E, U+2066–U+2069) — a right-to-left override would show the end of a value, or of the line after it, backwards — has it removed: the value reads in its own order, the characters around the control joined, and no such control is left in either part."""
    print_section(f"EMM-032: bidirectional controls in the {field} of {kind}")
    failures = []
    for control in BIDI_CONTROLS:
        content = _build(kind, **{field: f"zq-before{control}zq-after"})
        if "zq-beforezq-after" not in content.text or "zq-beforezq-after" not in content.html:
            failures.append(f"U+{ord(control):04X}: the value does not read in its own order")
        if any(left in content.text or left in content.html for left in BIDI_CONTROLS):
            failures.append(f"U+{ord(control):04X}: a bidirectional control is left in the e-mail")

    assert failures == [], "\n".join(failures)
    print_success(f"{len(BIDI_CONTROLS)} controls, all removed")


@pytest.mark.parametrize("kind", [ADMIN_SETUP, TEST], ids=["admin_setup", "test"])
def test_markup_across_a_line_break_is_still_escaped(kind: EmailKind) -> None:
    """EMM-033 — contract 7: a username ``<b>zq\\n<i>evil</i></b>``, markup split across a line feed, in a kind that still shows one: the text reads ``<b>zq <i>evil</i></b>`` on one line, and the HTML holds it escaped on one line — never as markup."""
    print_section(f"EMM-033: markup and a line feed in the username of {kind}")

    content = _build(kind, username="<b>zq\n<i>evil</i></b>")

    assert "<b>zq <i>evil</i></b>" in content.text, content.text
    assert html.escape("<b>zq <i>evil</i></b>") in content.html, "the username must be escaped, on one line, in the HTML"
    assert "<i>evil" not in content.html and "<b>zq" not in content.html, "markup from a username reached the HTML"
    print_success("one line in the text, escaped in the HTML")


# =============================================================================
# 8. THE NOTICE OF AN EMAIL CHANGE (lot E4a, then decision N62)
# =============================================================================


@pytest.mark.parametrize("language", LANGUAGES)
def test_each_catalogue_has_a_section_per_kind_and_nothing_else(language: str) -> None:
    """EMM-034 — contract 8: the sections of each catalogue are exactly the kinds of ``EmailKind`` — ``email_changed`` included — and ``common``: a kind without its texts, or texts without a kind, is a gap. ``email_changed`` has a subject, an intro and an advice, and no ``action``: it carries no link; the intro and the advice name the instance alone — the new address no longer (decision N62)."""
    print_section(f"EMM-034: sections of {language}.json")
    catalogue = _catalogue(language)

    assert set(catalogue) == {kind.value for kind in EmailKind} | {"common"}
    section = catalogue["email_changed"]
    assert set(section) == {"subject", "intro", "advice"}
    assert (set(string.Template(section["intro"]).get_identifiers()), set(string.Template(section["advice"]).get_identifiers())) == ({"instance"}, {"instance"})
    print_success(f"{len(EmailKind)} kinds and common; email_changed without an action")


@pytest.mark.parametrize("language", LANGUAGES)
def test_the_email_changed_notice_is_the_greeting_the_intro_the_advice_and_the_footer(language: str) -> None:
    """EMM-035 — contract 8: ``build_email_changed`` in each language: its kind, its language, the section's subject; the text is the anonymous greeting (``common.greeting_anonymous``: no username, decision N62), the intro with the instance, the advice with the instance, then the footer — nothing else, no link —; the HTML holds each of these escaped, and no ``href``, no button, not the button's fallback line."""
    print_section(f"EMM-035: email_changed in {language}")
    catalogue = _catalogue(language)
    section, common = catalogue["email_changed"], catalogue["common"]

    content = build_email_changed(language=language, instance=INSTANCE)

    values = {"instance": INSTANCE}
    blocks = [string.Template(text).substitute(values) for text in (common["greeting_anonymous"], section["intro"], section["advice"])]
    footer = string.Template(common["footer"]).substitute(values)
    assert (content.kind, content.language, content.subject) == (EMAIL_CHANGED, language, section["subject"])
    assert content.text == "\n\n".join(blocks) + f"\n\n-- \n{footer}\n"
    assert all(html.escape(block) in content.html for block in blocks), "each block, escaped, in the HTML"
    assert _hrefs(content.html) == [] and "<a " not in content.html, "no link and no button in the HTML"
    assert common["button_fallback"] not in content.text and html.escape(common["button_fallback"]) not in content.html
    assert "://" not in content.text
    print_success("anonymous greeting, intro, advice, footer; no link")


@pytest.mark.parametrize("language", LANGUAGES)
def test_the_notice_carries_no_part_of_the_new_address(language: str) -> None:
    """EMM-036 — contract 8: the notice cannot receive the new address — ``new_address`` is no parameter of ``build_email_changed`` — and carries no part of it: neither its local part nor its domain, in any letter case, nor a mask of it (``***``), in its subject, its text or its HTML. The domain is a host name its new owner chose freely, and mail clients make it a link (decision N62)."""
    print_section(f"EMM-036: no part of the new address in {language}")

    assert "new_address" not in inspect.signature(build_email_changed).parameters, "build_email_changed still takes the new address: the notice could show a domain its new owner chose"
    content = build_email_changed(language=language, instance=INSTANCE)

    for name, part in (("subject", content.subject), ("text", content.text), ("html", content.html)):
        shown = [piece for piece in (NEW_LOCAL_PART, NEW_DOMAIN, "***") if piece.casefold() in part.casefold()]
        assert shown == [], f"the {name} of the notice shows {shown}: no part of the new address"
    print_success("no part of the new address")


def test_masked_address_no_longer_exists() -> None:
    """EMM-037 — contract 8: ``messages.masked_address`` is gone — the notice was its only use, and shows no part of the new address any more (decision N62). The mask of an address an SMTP server quotes in its refusal is the delivery's own, ``delivery._redacted``, pinned in ``test_email_delivery.py``."""
    print_section("EMM-037: masked_address is gone")

    assert not hasattr(messages, "masked_address"), "messages.masked_address still exists: its only use, the notice, shows no part of the new address any more"
    print_success("no masked_address")


@pytest.mark.parametrize(
    "new_address",
    [
        pytest.param(NEW_ADDRESS, id="an-address-as-written"),
        pytest.param("zq@<b>evil</b>.example", id="markup-in-the-domain"),
        pytest.param("zq@evil.example\r\nBcc: zq-spy", id="a-cr-lf-and-a-header-in-the-domain"),
        pytest.param("zq@buy-cheap-zq-pills-now.example", id="a-domain-that-advertises"),
    ],
)
def test_a_new_address_cannot_reach_the_notice(new_address: str) -> None:
    """EMM-038 — contract 8 (and 9): a new address — as written, with markup or a CR LF and a header in its domain, or a domain that advertises: what the notice once showed as ``***@<domain>`` — cannot even be passed to ``build_email_changed``: a ``TypeError`` that names ``new_address``, and no notice built."""
    print_section(f"EMM-038: new_address={new_address!r}")

    with pytest.raises(TypeError, match="new_address"):
        build_email_changed(language="en", instance="zq-folio", new_address=new_address)
    print_success("TypeError: no notice can carry it")


# =============================================================================
# 9. NO TEXT OF AN UNTRUSTED PARTY (decision N62, E-9 b and c)
# =============================================================================

#: A username as whoever signs up may write it: markup, a link to a site of their own, a CR LF and a header after it.
CRAFTED_USERNAME = '<a href="http://zq-spam.example/x">zq-claim-your-prize</a>\r\nBcc: zq-spy@zq-spam.example'
#: Its pieces: any of them in an e-mail would be text its writer chose.
CRAFTED_PIECES = ("zq-spam.example", "zq-claim-your-prize", "zq-spy")
#: The kinds an untrusted party can address — a stranger's «forgot password», a sign-up, an email change —: no username.
UNTRUSTED_KINDS = (PASSWORD_RESET, EMAIL_VERIFICATION, EMAIL_CHANGED)
#: The kinds whose sender is trusted — the operator, an administrator writing to themselves —: they keep the username.
TRUSTED_KINDS = (ADMIN_SETUP, TEST)
#: A paragraph of the HTML body; the first one is where the greeting goes.
_PARAGRAPH_HTML = re.compile(r"<p\b[^>]*>(.*?)</p>", re.DOTALL)


@pytest.mark.parametrize("language", LANGUAGES)
@pytest.mark.parametrize("kind", UNTRUSTED_KINDS, ids=str)
def test_an_email_an_untrusted_party_can_address_greets_nobody_by_name(kind: EmailKind, language: str) -> None:
    """EMM-039 — contract 9: ``username`` is no parameter of the builder, so a crafted one — markup, a link to ``http://zq-spam.example/x``, a CR LF and a header — cannot even be passed: a ``TypeError`` naming it. The e-mail opens with exactly ``common.greeting_anonymous`` — the text's first block as written, the HTML's first paragraph escaped —, and nothing of the crafted username is in its subject, its text or its HTML."""
    print_section(f"EMM-039: {kind} in {language} greets nobody by name")
    builder, arguments = BUILDERS[kind]
    anonymous = _catalogue(language)["common"]["greeting_anonymous"]

    assert "username" not in inspect.signature(builder).parameters, f"{builder.__name__} still takes a username: whoever can address this e-mail chooses it"
    with pytest.raises(TypeError, match="username"):
        builder(**{"language": language, **arguments, "username": CRAFTED_USERNAME})
    content = _build(kind, language)

    assert content.text.split("\n\n", 1)[0] == anonymous, f"the text does not open with {anonymous!r}: {content.text!r}"
    assert _PARAGRAPH_HTML.search(content.html).group(1) == html.escape(anonymous), "the HTML does not open with the anonymous greeting"
    parts = {"subject": content.subject, "text": content.text, "html": html.unescape(content.html)}
    assert [(name, piece) for name, part in parts.items() for piece in CRAFTED_PIECES if piece in part] == [], "a piece of the crafted username reached the e-mail"
    print_success(f"{anonymous!r}; no username can be passed")


@pytest.mark.parametrize("language", LANGUAGES)
@pytest.mark.parametrize("kind", TRUSTED_KINDS, ids=str)
def test_the_admin_setup_and_the_test_email_still_greet_by_name(kind: EmailKind, language: str) -> None:
    """EMM-040 — contract 9, a guard: ``build_admin_setup`` and ``build_test_message``, whose sender is trusted — the operator, an administrator writing to themselves —, still take ``username`` and open with ``common.greeting`` and the username: the text's first block as written, the HTML's first paragraph escaped. Green before decision N62's cure and after it."""
    print_section(f"EMM-040: {kind} in {language} greets by name")
    builder, _arguments = BUILDERS[kind]
    greeting = string.Template(_catalogue(language)["common"]["greeting"]).substitute(username=USERNAME)

    content = _build(kind, language)

    assert "username" in inspect.signature(builder).parameters, f"{builder.__name__} lost its username: its sender is trusted"
    assert content.text.split("\n\n", 1)[0] == greeting, f"the text does not open with {greeting!r}"
    assert _PARAGRAPH_HTML.search(content.html).group(1) == html.escape(greeting), "the HTML does not open with the greeting and the username, escaped"
    print_success(repr(greeting))


@pytest.mark.parametrize("language", LANGUAGES)
def test_no_text_of_the_three_kinds_has_a_place_for_a_username_or_the_new_address(language: str) -> None:
    """EMM-041 — contract 9: in each catalogue, no text of the sections an untrusted party can address — ``password_reset``, ``email_verification``, ``email_changed`` — holds ``$username``; ``email_changed.intro`` holds no ``$address`` and still holds ``$instance``; and the greeting they open with, ``common.greeting_anonymous``, holds no placeholder at all."""
    print_section(f"EMM-041: placeholders of {language}.json")
    catalogue = _catalogue(language)
    identifiers = {f"{kind}.{key}": set(string.Template(text).get_identifiers()) for kind in UNTRUSTED_KINDS for key, text in catalogue[kind.value].items()}

    assert sorted(path for path, names in identifiers.items() if "username" in names) == [], "a text of these sections has a place for a username"
    intro = identifiers["email_changed.intro"]
    assert "address" not in intro, f"email_changed.intro still has a place for the new address: {sorted(intro)}"
    assert "instance" in intro, f"email_changed.intro lost the instance: {sorted(intro)}"
    assert string.Template(catalogue["common"]["greeting_anonymous"]).get_identifiers() == [], "the anonymous greeting has a placeholder"
    print_success("no $username, no $address; $instance kept")
