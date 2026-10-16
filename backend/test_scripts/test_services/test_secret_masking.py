"""Masking of the secrets a plugin call carries, in its errors and in the log lines written meanwhile (plan 03, CP10).

Module under test: ``utils/runtime/secret_masking.py``, and its wiring in ``logging_config.configure_logging``. The
contract pinned here, hardened after the security review:

1. ``mask_text`` replaces each secret by ``***``, and its URL-encoded forms (``quote`` and ``quote_plus``) too; by
   default the secrets in flight; an empty secret masks nothing. Every occurrence of every form is found in the
   original text, and each run of occurrences that overlap or touch becomes one ``***``: a secret inside another, beside
   itself, or overlapped by a value a caller chose — the overlap attack of the security review of CP10–CP11, a known
   context and one guessed character — leaves no character of itself behind. With ``whole``, a text that shows a
   secret becomes ``***`` entirely and a text that shows none comes back as it was: two guesses read the same (N15).
2. Any value is judged by the text it shows. Strings are masked; plain dicts, lists, tuples and sets are copied with
   their keys and items masked; any other value — bytes, a number, a URL object, an exception kept as a detail, a dict
   subclass — that shows a secret in its ``str()`` or its ``repr()`` becomes its masked text, and one that shows none is
   handed back as the very same object.
3. ``mask_exception`` masks in place the arguments, every attribute of the instance that shows a secret (``message``,
   ``details``, the notes, a plugin's own attribute), an ``OSError``'s text and file names, through the whole
   ``__cause__`` / ``__context__`` chain and the members of exception groups; type and traceback stay. What it cannot
   rewrite — a group's own message, a text a ``__str__`` builds from state outside ``__dict__`` (``__slots__``) — is what
   ``exception_renders_secret`` reports (the text, or the notes, of any link); ``masked_description`` gives
   ``Type: text`` masked, what a boundary says of an error it has to replace. With ``whole``, every text that shows a
   secret — an argument, ``message``, a detail, a note, a cause — becomes ``***`` entirely, the rest as it was, type,
   code and traceback kept; ``masked_description`` is then ``Type: ***``.
4. ``mask_event_dict`` (structlog) masks every value of an event, the formatted traceback included, and hands back the
   same dict when nothing is in flight; ``SecretMaskingFilter`` (standard ``logging``) replaces the formatted message
   and the traceback text of a record by their masked text and leaves a record with nothing to mask as it was.
5. The secrets are in flight inside ``secrets_in_flight`` only: they reach ``asyncio.to_thread`` and the tasks created
   after they are set, nested blocks add up and undo in order; outside, nothing is masked.
6. The wiring: ``configure_logging`` puts the filter on its handlers and ``mask_event_dict`` right after
   ``format_exc_info`` and before the JSON renderer. A line logged through structlog or a standard logger while a secret
   is in flight — message, values, traceback, a value that is no string, a secret with characters JSON escapes —
   reaches the handler with no part of the secret; the same lines outside the block show it (the negative control).

Pure: no database, no server, no network. The logging state ``configure_logging`` changes — every logger, the root
handlers, structlog's configuration — is put back on the way out of each block that calls it.
"""

from __future__ import annotations

import asyncio
import contextlib
import io
import logging
import sys
import uuid
from collections.abc import Iterator
from urllib.parse import quote, quote_plus

import pytest
import structlog

from backend.app.logging_config import configure_logging
from backend.app.services.assets.base import AssetSourceError
from backend.app.utils.runtime.secret_masking import (
    MASK,
    SecretMaskingFilter,
    active_secrets,
    exception_renders_secret,
    mask_event_dict,
    mask_exception,
    mask_text,
    masked_description,
    secrets_in_flight,
)
from backend.test_scripts.test_utils import print_section, print_success


def _secret(tail: str = "") -> str:
    """A unique secret: ``lfsecret`` and 16 hex characters (its core, see ``_core``), then ``tail``."""
    return f"lfsecret{uuid.uuid4().hex[:16]}{tail}"


def _core(secret: str) -> str:
    """The unique part of a secret: any rendering of the secret that leaks it, escaped or encoded, still holds it."""
    return secret[:24]


def _forms(secret: str) -> set[str]:
    return {secret, quote(secret, safe=""), quote_plus(secret)}


def _shows(text: str, secret: str) -> list[str]:
    """The forms of ``secret`` that ``text`` still shows."""
    return sorted(form for form in _forms(secret) if form in text)


class _Url:
    """A URL object, as an HTTP library keeps one: its text is the URL, its representation wraps it."""

    def __init__(self, raw: str):
        self.raw = raw

    def __str__(self) -> str:
        return self.raw

    def __repr__(self) -> str:
        return f"URL({self.raw!r})"


class _Params(dict):
    """A dict subclass: not copied like a plain dict, judged by its text."""


class _SlotsLeak(Exception):
    """A plugin's error whose text a ``__str__`` builds from state outside ``__dict__``: masking cannot reach it."""

    __slots__ = ("_hidden",)

    def __init__(self, hidden: str):
        super().__init__("opaque")
        self._hidden = hidden

    def __str__(self) -> str:
        return f"failed with {self._hidden}"


class _AttributeLeak(Exception):
    """A plugin's error whose ``__str__`` reads a normal attribute: masked in place."""

    def __init__(self, hidden: str):
        super().__init__("attribute")
        self.hidden = hidden

    def __str__(self) -> str:
        return f"failed with {self.hidden}"


# =============================================================================
# 1. mask_text
# =============================================================================


def test_mask_text_replaces_the_value_and_its_url_encoded_forms():
    """1: the value as written, ``quote(value, safe="")`` and ``quote_plus(value)``: how a key in a query string shows."""
    print_section("1: mask_text and the URL forms")
    secret = _secret(" p@ss/w+rd&é")
    assert len(_forms(secret)) == 3, "setup: the three forms must differ, or the test proves one of them only"
    text = f"raw={secret} quoted={quote(secret, safe='')} plus={quote_plus(secret)} end"

    masked = mask_text(text, frozenset({secret}))

    assert masked == f"raw={MASK} quoted={MASK} plus={MASK} end"
    print_success("raw, quote and quote_plus forms all masked")


def test_a_secret_inside_another_is_masked_whole():
    """1: ``abcd1234efgh`` is masked whole, not as ``***efgh``: the two occurrences overlap, one ``***``."""
    short, long = "abcd1234", "abcd1234efgh"

    assert mask_text(f"a {long} b {short} c", frozenset({short, long})) == f"a {MASK} b {MASK} c"


def test_mask_text_masks_the_secrets_in_flight_by_default_and_nothing_outside():
    secret = _secret()
    text = f"token {secret} sent"

    with secrets_in_flight(frozenset({secret})):
        inside = mask_text(text)
    outside = mask_text(text)

    assert inside == f"token {MASK} sent"
    assert outside == text


@pytest.mark.parametrize(
    ("text", "values"),
    [pytest.param("nothing secret here", frozenset(), id="no-secret"), pytest.param("", frozenset({"s3cret-value"}), id="empty-text"), pytest.param("abc", frozenset({""}), id="empty-secret")],
)
def test_mask_text_leaves_the_text_when_there_is_nothing_to_mask(text, values):
    """1: no secret, an empty text, or an empty secret (which would otherwise match everywhere): the text as it was."""
    assert mask_text(text, values) == text


# -----------------------------------------------------------------------------
# Overlapping occurrences, the overlap attack and ``whole`` (security review of CP10–CP11, N15)
# -----------------------------------------------------------------------------

#: What a refused request shows right before an instance key, as an HTTP library writes it: anybody can read it in the
#: plugin's code. Longer than a key, so a value chosen as this context and one character is the longer of the two: the
#: order in which replacing the longest form first let the right guess take the key's first character with it.
_KNOWN_CONTEXT = "Client error '401 Unauthorized' for url 'https://api.provider.example/v1/quote?symbol=msft&apikey="
_AFTER_THE_KEY = "' refused"
#: The letters of the instance keys below: none occurs in the context or after the key, so any character of a key left
#: in an output shows as such.
_KEY_LETTERS = "BDFGHJLNPQRSTVWZ"


def _instance_key() -> str:
    """A unique instance key: 24 characters of ``_KEY_LETTERS``."""
    return "".join(_KEY_LETTERS[int(digit, 16)] for digit in uuid.uuid4().hex[:24])


def _chosen(key: str, *, right: bool) -> str:
    """The personal secret a caller chooses to test a guess of ``key``'s first character: the known context, then the
    guess — the right one, or another letter a key may start with."""
    guess = key[0] if right else next(letter for letter in _KEY_LETTERS if letter != key[0])
    return _KNOWN_CONTEXT + guess


def _echoed(key: str) -> str:
    """The text of the error: the known context, the key, what follows it."""
    return f"{_KNOWN_CONTEXT}{key}{_AFTER_THE_KEY}"


@pytest.mark.parametrize("right", [False, True], ids=["a-wrong-guess", "the-right-guess"])
def test_the_overlap_attack_leaves_no_character_of_the_key(right: bool):
    """1, the overlap attack: an instance key behind a known context, and a value the caller chose — that context and
    one guessed character — longer than the key. Replaced one form after another, the longest first, the right guess
    took the key's first character with it and left the rest of the key in clear; found all at once and merged, the
    output shows no character of the key, whichever the guess."""
    print_section(f"1: the overlap attack, {'the right' if right else 'a wrong'} guess")
    key = _instance_key()
    chosen, text = _chosen(key, right=right), _echoed(key)
    assert len(chosen) > len(key), "setup: the chosen value is the longer one"
    assert not set(key) & set(text.replace(key, "")), "setup: only the key uses the key's letters"

    masked = mask_text(text, frozenset({key, chosen}))

    assert not set(masked) & set(key), f"the output shows part of the key: {masked!r}"
    assert masked == (f"{MASK}{_AFTER_THE_KEY}" if right else f"{_KNOWN_CONTEXT}{MASK}{_AFTER_THE_KEY}"), "one *** per run of overlapping occurrences"
    print_success(f"no character of the key: {masked!r}")


def test_with_whole_the_two_guesses_give_the_same_output():
    """1, N15: masked in place, the two guesses still read differently — the known context is masked with the right one
    only, an oracle a character at a time. With ``whole`` a text that shows a secret is ``***`` entirely: byte for byte
    the same output, whichever the guess."""
    key = _instance_key()
    text = _echoed(key)
    wrong, right = frozenset({key, _chosen(key, right=False)}), frozenset({key, _chosen(key, right=True)})
    assert mask_text(text, wrong) != mask_text(text, right), "barrier: masked in place, the output tells the guesses apart"

    hidden = {"wrong": mask_text(text, wrong, whole=True), "right": mask_text(text, right, whole=True)}

    assert hidden["wrong"] == hidden["right"] == MASK, hidden


@pytest.mark.parametrize(
    ("text", "values", "expected"),
    [
        pytest.param("x AAAA1111BBBB2222 y", {"AAAA1111", "BBBB2222"}, f"x {MASK} y", id="two-secrets-touching"),
        pytest.param("x AAAA1111BBBB y", {"AAAA1111", "1111BBBB"}, f"x {MASK} y", id="two-secrets-overlapping"),
        pytest.param("x CCCC3333CCCC3333 y", {"CCCC3333"}, f"x {MASK} y", id="one-secret-twice-in-a-row"),
        pytest.param("x xyzxyzxyz y", {"xyzxyz"}, f"x {MASK} y", id="one-secret-overlapping-itself"),
        pytest.param("x AAAA1111 BBBB2222 y", {"AAAA1111", "BBBB2222"}, f"x {MASK} {MASK} y", id="apart-a-mask-each"),
    ],
)
def test_occurrences_that_overlap_or_touch_become_one_mask(text: str, values: set[str], expected: str):
    """1: every occurrence of every form is found in the original text; a run of occurrences that overlap or touch is
    one ``***`` — nothing of a secret is left beside another, nor beside itself —; occurrences apart get one each."""
    assert mask_text(text, frozenset(values)) == expected


@pytest.mark.parametrize(
    ("build", "in_place"),
    [
        pytest.param(lambda secret: f"first {secret}, again {secret}, once more {secret}.", f"first {MASK}, again {MASK}, once more {MASK}.", id="several-occurrences"),
        pytest.param(lambda secret: f"GET /q?raw={secret}&k={quote(secret, safe='')}&j={quote_plus(secret)} failed", f"GET /q?raw={MASK}&k={MASK}&j={MASK} failed", id="the-url-encoded-forms"),
    ],
)
def test_whole_hides_a_text_wherever_and_however_it_shows_a_secret(build, in_place: str):
    """1, N15: several occurrences, the URL-encoded forms: masked in place each has its own ``***``; with ``whole`` the
    whole text is ``***``."""
    secret = _secret(" p@ss/w+rd&é")
    text = build(secret)

    assert mask_text(text, frozenset({secret})) == in_place
    assert mask_text(text, frozenset({secret}), whole=True) == MASK


@pytest.mark.parametrize(
    ("text", "values"),
    [
        pytest.param("the provider answered 404 for MOCK", frozenset({"lfsecret-not-in-this-text"}), id="no-secret-in-the-text"),
        pytest.param(_KNOWN_CONTEXT, frozenset({"lfsecret-not-in-this-text"}), id="the-known-context-alone"),
        pytest.param("nothing secret here", frozenset(), id="no-secret-at-all"),
        pytest.param("", frozenset({"s3cret-value"}), id="empty-text"),
        pytest.param("abc", frozenset({""}), id="empty-secret"),
    ],
)
def test_with_whole_a_text_that_shows_no_secret_comes_back_as_it_was(text: str, values: frozenset[str]):
    """1, N15: ``whole`` hides only a text that shows a secret; an empty secret, which would match everywhere, hides
    nothing."""
    assert mask_text(text, values, whole=True) == text


# =============================================================================
# 2. ANY VALUE, JUDGED BY ITS TEXT
# =============================================================================


def _masked(value: object, secret: str) -> object:
    """What an event value becomes while ``secret`` is in flight."""
    with secrets_in_flight(frozenset({secret})):
        return mask_event_dict(None, "info", {"value": value})["value"]


def test_the_keys_and_items_of_plain_containers_are_masked():
    """2: a dict's keys too: a secret can be the key of a mapping a plugin logs."""
    secret = _secret()

    masked = _masked({f"key-{secret}": [secret, (secret, 1)], "n": {secret}}, secret)

    assert masked == {f"key-{MASK}": [MASK, (MASK, 1)], "n": {MASK}}


@pytest.mark.parametrize(
    ("build", "expected"),
    [
        pytest.param(lambda secret: secret.encode("utf-8"), lambda masked: masked == f"b'{MASK}'", id="bytes"),
        pytest.param(lambda secret: _Url(f"https://api.example/q?apikey={quote_plus(secret)}"), lambda masked: masked == f"https://api.example/q?apikey={MASK}", id="url-object"),
        pytest.param(lambda secret: RuntimeError(f"refused {secret}"), lambda masked: masked == f"refused {MASK}", id="exception-as-a-detail"),
        pytest.param(lambda secret: _Params(token=secret), lambda masked: masked == f"{{'token': '{MASK}'}}", id="dict-subclass"),
    ],
)
def test_a_value_that_shows_a_secret_becomes_its_masked_text(build, expected):
    """2: a value that is no plain container is judged by its ``str()`` (else its ``repr()``) and becomes that text, masked."""
    secret = _secret()

    masked = _masked(build(secret), secret)

    assert isinstance(masked, str) and expected(masked), masked


def test_a_number_that_is_a_secret_becomes_masked_text():
    """2: a PIN or a numeric key logged as a number."""
    digits = str(uuid.uuid4().int)[:16]
    assert _masked(int(digits), digits) == MASK


@pytest.mark.parametrize(
    "value",
    [
        pytest.param(b"plain bytes", id="bytes"),
        pytest.param(42, id="int"),
        pytest.param(3.5, id="float"),
        pytest.param(None, id="none"),
        pytest.param(_Url("https://api.example/q?page=2"), id="url-object"),
        pytest.param(RuntimeError("nothing secret"), id="exception"),
        pytest.param(_Params(page=2), id="dict-subclass"),
    ],
)
def test_a_value_that_shows_no_secret_is_the_same_object(value):
    """2: nothing to mask, nothing replaced: the very object comes back (a renderer keeps its own way of writing it)."""
    assert _masked(value, _secret()) is value


# =============================================================================
# 3. mask_exception, exception_renders_secret, masked_description
# =============================================================================


def test_mask_exception_masks_the_arguments_nested_ones_included():
    """3: strings in the arguments, and in the lists, tuples, sets and dicts among them; other values untouched."""
    print_section("3: mask_exception, the arguments")
    secret = _secret()
    error = RuntimeError(f"failed with {secret}", [f"in a list {secret}", 42], {"key": secret, "n": 1}, (secret,), {secret}, 3.5)

    mask_exception(error, frozenset({secret}))

    assert error.args == (f"failed with {MASK}", [f"in a list {MASK}", 42], {"key": MASK, "n": 1}, (MASK,), {MASK}, 3.5)
    assert secret not in str(error) and secret not in repr(error)
    print_success("every string argument masked, the others kept")


def test_mask_exception_masks_message_and_details_and_keeps_the_rest():
    """3: an ``AssetSourceError``: ``message``, ``details`` (an encoded URL, a URL object) and ``str()``; code, type and traceback stay."""
    secret = _secret("/k+y")
    try:
        raise AssetSourceError(f"provider refused key {secret}", "AUTH_FAILED", {"url": f"https://api.example/q?apikey={quote_plus(secret)}", "request": _Url(f"https://api.example/q?k={secret}"), "status": 401})
    except AssetSourceError as caught:
        error = caught
    traceback_before = error.__traceback__

    mask_exception(error, frozenset({secret}))

    assert error.message == f"provider refused key {MASK}"
    assert error.details == {"url": f"https://api.example/q?apikey={MASK}", "request": f"https://api.example/q?k={MASK}", "status": 401}
    assert str(error) == f"provider refused key {MASK}"
    assert type(error) is AssetSourceError and error.error_code == "AUTH_FAILED"
    assert error.__traceback__ is traceback_before, "the traceback must stay: the callers log and re-raise it"


def test_mask_exception_masks_the_notes_and_the_attributes_of_a_plugins_own_error():
    """3: ``__notes__`` and any instance attribute that shows a secret; an attribute that shows none is left as it is."""
    secret = _secret()
    error = _AttributeLeak(secret)
    error.url = _Url(f"https://api.example/q?apikey={secret}")
    error.status = 401
    error.add_note(f"while calling with key {secret}")

    mask_exception(error, frozenset({secret}))

    assert str(error) == f"failed with {MASK}" and type(error) is _AttributeLeak, "a __str__ over a normal attribute comes out masked, type kept"
    assert error.url == f"https://api.example/q?apikey={MASK}"
    assert error.__notes__ == [f"while calling with key {MASK}"]
    assert error.status == 401
    assert not exception_renders_secret(error, frozenset({secret}))


def test_mask_exception_masks_an_oserrors_text_and_file_names():
    """3: ``str()`` of an ``OSError`` is built from ``strerror``, ``filename`` and ``filename2``, not from its arguments."""
    secret = _secret()
    error = OSError(2, f"no such file for {secret}", f"/tmp/{secret}.json", None, f"/tmp/backup-{secret}.json")
    assert secret in str(error), "setup: the three attributes show the secret"

    mask_exception(error, frozenset({secret}))

    assert (error.strerror, error.filename, error.filename2) == (f"no such file for {MASK}", f"/tmp/{MASK}.json", f"/tmp/backup-{MASK}.json")
    assert secret not in str(error) and error.errno == 2


def test_mask_exception_follows_the_cause_and_context_chain():
    """3: an error raised ``from`` another, itself raised while handling a third: all three masked."""
    secret = _secret()
    try:
        try:
            try:
                raise KeyError(f"lookup {secret}")
            except KeyError:
                raise ValueError(f"while handling {secret}")  # noqa: B904 — the implicit __context__ is the point
        except ValueError as context_error:
            raise RuntimeError(f"wrapper {secret}") from context_error
    except RuntimeError as caught:
        error = caught
    assert exception_renders_secret(error, frozenset({secret})), "barrier: before masking the chain shows the secret"

    mask_exception(error, frozenset({secret}))

    chain = [error, error.__cause__, error.__cause__.__context__]
    assert [type(link) for link in chain] == [RuntimeError, ValueError, KeyError], "setup: the chain is cause, then context"
    assert all(secret not in str(link) for link in chain), [str(link) for link in chain]
    assert not exception_renders_secret(error, frozenset({secret}))


def test_mask_exception_survives_a_cycle_in_the_chain():
    """3: an error that is its own context two links away is visited once: masking and the check both end."""
    secret = _secret()
    first, second = ValueError(secret), RuntimeError(secret)
    first.__context__, second.__context__ = second, first

    mask_exception(first, frozenset({secret}))

    assert first.args == (MASK,) and second.args == (MASK,)
    assert not exception_renders_secret(first, frozenset({secret}))


def test_mask_exception_masks_the_members_of_an_exception_group():
    """3: every member of a group, nested groups included; the group then shows nothing."""
    secret = _secret()
    inner = ExceptionGroup("inner", [KeyError(secret)])
    group = ExceptionGroup("several providers failed", [ValueError(f"first {secret}"), inner])
    assert exception_renders_secret(group, frozenset({secret})), "barrier: a member shows the secret before masking"

    mask_exception(group, frozenset({secret}))

    members = [group.exceptions[0], inner.exceptions[0]]
    assert all(secret not in str(member) for member in members), [str(member) for member in members]
    assert type(group) is ExceptionGroup and len(group.exceptions) == 2
    assert not exception_renders_secret(group, frozenset({secret}))


@pytest.mark.parametrize(
    "build",
    [
        pytest.param(lambda secret: ExceptionGroup(f"calls with key {secret} failed", [ValueError("first")]), id="a-groups-own-message"),
        pytest.param(lambda secret: _SlotsLeak(secret), id="a-__str__-over-__slots__"),
        pytest.param(lambda secret: _chained(_SlotsLeak(secret)), id="such-an-error-as-a-cause"),
    ],
)
def test_what_masking_cannot_rewrite_exception_renders_secret_reports(build):
    """3: text built outside the arguments and ``__dict__`` survives ``mask_exception``: the check says so, the boundary replaces it."""
    secret = _secret()
    error = build(secret)

    mask_exception(error, frozenset({secret}))

    assert exception_renders_secret(error, frozenset({secret})), f"the check must see what masking left: {[str(link) for link in _links(error)]}"


def _chained(cause: BaseException) -> BaseException:
    """A ``RuntimeError`` raised ``from`` ``cause``."""
    try:
        try:
            raise cause
        except BaseException as inner:
            raise RuntimeError("the call failed") from inner
    except RuntimeError as outer:
        return outer


def _links(error: BaseException) -> list[BaseException]:
    return [error, *(link for link in (error.__cause__, error.__context__) if link is not None)]


def test_a_secret_only_in_the_notes_is_reported():
    """3: the notes are part of what a traceback shows."""
    secret = _secret()
    error = RuntimeError("plain")
    error.add_note(f"key {secret}")

    assert exception_renders_secret(error, frozenset({secret}))
    assert not exception_renders_secret(error, frozenset()), "without secrets nothing is reported"
    assert not exception_renders_secret(RuntimeError("plain"), frozenset({secret}))


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        pytest.param(ValueError("bad key lfsecret-description-0001"), f"ValueError: bad key {MASK}", id="with-text"),
        pytest.param(_SlotsLeak("lfsecret-description-0001"), f"_SlotsLeak: failed with {MASK}", id="text-of-a-__str__"),
        pytest.param(ValueError(), "ValueError", id="without-text"),
    ],
)
def test_masked_description_is_type_and_text_masked(error, expected):
    """3: what a boundary says of an error it replaces: ``Type: text``, masked; the type alone without a text."""
    assert masked_description(error, frozenset({"lfsecret-description-0001"})) == expected


def test_mask_exception_without_secrets_changes_nothing():
    error = RuntimeError("nothing secret", {"k": "v"})
    mask_exception(error, frozenset())
    assert error.args == ("nothing secret", {"k": "v"})


def test_with_whole_every_text_of_an_error_that_shows_a_secret_is_hidden_and_the_rest_stays():
    """3, N15: ``whole`` through ``mask_exception``: the argument, ``message``, each detail, the note and the cause that
    show the secret become ``***`` entirely; the details that show none, the code, the type and the traceback stay."""
    print_section("3: mask_exception with whole")
    secret = _secret("/k+y")
    try:
        try:
            raise ConnectionError(f"GET https://api.example/q?apikey={quote_plus(secret)} refused")
        except ConnectionError as cause:
            raise AssetSourceError(f"provider refused key {secret}", "AUTH_FAILED", {"url": f"https://api.example/q?apikey={quote_plus(secret)}", "request": _Url(f"https://api.example/q?k={secret}"), "status": 401, "hint": "check the key"}) from cause
    except AssetSourceError as caught:
        error = caught
    error.add_note(f"while calling with key {secret}")
    traceback_before = error.__traceback__

    mask_exception(error, frozenset({secret}), whole=True)

    assert (error.args, error.message, str(error)) == ((MASK,), MASK, MASK)
    assert error.details == {"url": MASK, "request": MASK, "status": 401, "hint": "check the key"}
    assert error.__notes__ == [MASK]
    assert (error.__cause__.args, str(error.__cause__)) == ((MASK,), MASK)
    assert type(error) is AssetSourceError and error.error_code == "AUTH_FAILED"
    assert error.__traceback__ is traceback_before
    assert not exception_renders_secret(error, frozenset({secret}))
    print_success("each text that showed the secret is ***, the rest as it was")


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        pytest.param(ValueError("bad key lfsecret-description-0001 for https://api.example"), f"ValueError: {MASK}", id="with-text"),
        pytest.param(_SlotsLeak("lfsecret-description-0001"), f"_SlotsLeak: {MASK}", id="text-of-a-__str__"),
        pytest.param(ValueError("bad key, nothing secret in it"), "ValueError: bad key, nothing secret in it", id="a-text-without-a-secret"),
        pytest.param(ValueError(), "ValueError", id="without-text"),
    ],
)
def test_masked_description_with_whole_is_the_type_and_a_mask(error, expected):
    """3, N15: what a boundary says of an error it replaces when the caller chose a secret: ``Type: ***``; a text that
    shows no secret as it is; the type alone without a text."""
    assert masked_description(error, frozenset({"lfsecret-description-0001"}), whole=True) == expected


# =============================================================================
# 4. mask_event_dict and SecretMaskingFilter
# =============================================================================


def test_mask_event_dict_masks_every_value_and_keeps_the_keys_without_secrets():
    """4: the event, the values, the nested ones, the formatted traceback; other values and the keys as they were."""
    print_section("4: mask_event_dict")
    secret = _secret()
    event = {"event": f"called with {secret}", "url": f"https://x/?k={quote(secret, safe='')}", "nested": {"list": [secret, 1]}, "exception": f"Traceback ...\nRuntimeError: {secret}", "count": 3}

    with secrets_in_flight(frozenset({secret})):
        masked = mask_event_dict(None, "warning", event)

    assert masked == {"event": f"called with {MASK}", "url": f"https://x/?k={MASK}", "nested": {"list": [MASK, 1]}, "exception": f"Traceback ...\nRuntimeError: {MASK}", "count": 3}
    print_success("strings masked at every depth, keys and numbers kept")


def test_mask_event_dict_hands_back_the_same_event_when_nothing_is_in_flight():
    event = {"event": "plain", "value": "lfsecret-not-in-flight"}
    assert mask_event_dict(None, "info", event) is event


def _record(msg: str, args: tuple = (), exc_info=None) -> logging.LogRecord:
    return logging.LogRecord("lf.test.library", logging.WARNING, __file__, 1, msg, args, exc_info)


def test_the_filter_masks_the_formatted_message_and_drops_the_arguments():
    """4: the message is formatted once and replaced by its masked text; the record still passes."""
    secret = _secret()
    record = _record("GET %s failed with %d", (f"https://x/?apikey={secret}", 401))

    with secrets_in_flight(frozenset({secret})):
        passed = SecretMaskingFilter().filter(record)

    assert passed is True
    assert record.getMessage() == f"GET https://x/?apikey={MASK} failed with 401"
    assert record.args is None


def test_the_filter_masks_the_traceback_text():
    """4: a record with ``exc_info``: the traceback is formatted and masked; a pre-formatted ``exc_text`` too."""
    secret = _secret()
    try:
        raise RuntimeError(f"token {secret} refused")
    except RuntimeError:
        record = _record("call failed", exc_info=sys.exc_info())
    preformatted = _record("call failed")
    preformatted.exc_text = f"Traceback\nRuntimeError: {secret}"

    with secrets_in_flight(frozenset({secret})):
        SecretMaskingFilter().filter(record)
        SecretMaskingFilter().filter(preformatted)

    assert record.exc_text and "RuntimeError" in record.exc_text and secret not in record.exc_text
    assert preformatted.exc_text == f"Traceback\nRuntimeError: {MASK}"
    assert record.getMessage() == "call failed"


def test_the_filter_leaves_a_record_with_nothing_to_mask_as_it_was():
    """4: no secret in flight, or none in the record: message, arguments and traceback text untouched."""
    secret = _secret()
    args = ("https://x/?page=2",)
    outside = _record("GET %s", args)
    unrelated = _record("GET %s", args)

    SecretMaskingFilter().filter(outside)
    with secrets_in_flight(frozenset({secret})):
        SecretMaskingFilter().filter(unrelated)

    for record in (outside, unrelated):
        assert record.msg == "GET %s" and record.args is args and record.exc_text is None


# =============================================================================
# 5. IN FLIGHT: THE CONTEXT VARIABLE
# =============================================================================


def test_nested_blocks_add_up_and_undo_in_order():
    first, second = _secret(), _secret()
    assert active_secrets() == frozenset()
    with secrets_in_flight(frozenset({first})):
        with secrets_in_flight(frozenset({second})):
            assert active_secrets() == frozenset({first, second})
        assert active_secrets() == frozenset({first})
        with secrets_in_flight(frozenset()):
            assert active_secrets() == frozenset({first}), "an empty block changes nothing"
    assert active_secrets() == frozenset()


@pytest.mark.asyncio
async def test_the_secrets_reach_to_thread_and_the_tasks_created_after_they_are_set():
    """5: ``asyncio.to_thread`` copies the context into the worker thread; a task copies it when it is created."""
    print_section("5: the context variable across threads and tasks")
    secret = _secret()
    gate = asyncio.Event()

    async def read_when_released() -> frozenset[str]:
        await gate.wait()
        return active_secrets()

    created_before = asyncio.create_task(read_when_released())
    with secrets_in_flight(frozenset({secret})):
        created_inside = asyncio.create_task(read_when_released())
        in_thread = await asyncio.to_thread(active_secrets)
        masked_in_thread = await asyncio.to_thread(mask_text, f"key={secret}")
    gate.set()

    assert in_thread == frozenset({secret})
    assert masked_in_thread == f"key={MASK}"
    assert await created_inside == frozenset({secret}), "a task created while the secret is in flight keeps it"
    assert await created_before == frozenset(), "a task created before the block does not see it"
    assert active_secrets() == frozenset() and await asyncio.to_thread(active_secrets) == frozenset()
    print_success("worker thread and new task see the secret; the older task and the outside do not")


# =============================================================================
# 6. THE WIRING IN configure_logging
# =============================================================================


@contextlib.contextmanager
def _logging_state_restored() -> Iterator[None]:
    """Every logger (level, handlers, filters, propagate, disabled) and structlog's configuration, put back on the way out.

    A handler the block attached, and that no logger held before, is closed. The root handlers put back are the ones
    pytest attached for this test.
    """

    def every_logger() -> dict[str, logging.Logger]:
        return {"": logging.getLogger(), **{name: logger for name, logger in logging.Logger.manager.loggerDict.items() if isinstance(logger, logging.Logger)}}

    before = {name: (logger.level, list(logger.handlers), list(logger.filters), logger.propagate, logger.disabled) for name, logger in every_logger().items()}
    held = {handler for _level, handlers, *_rest in before.values() for handler in handlers}
    configured, config = structlog.is_configured(), structlog.get_config()
    try:
        yield
    finally:
        added = set()
        for name, logger in every_logger().items():
            level, handlers, filters, propagate, disabled = before.get(name, (logging.NOTSET, [], [], True, False))
            added.update(handler for handler in logger.handlers if handler not in held)
            logger.handlers[:], logger.filters[:] = handlers, filters
            logger.propagate, logger.disabled = propagate, disabled
            logger.setLevel(level)
        for handler in added:
            handler.close()
        if configured:
            structlog.configure(**config)
        else:
            structlog.reset_defaults()


def _configured_with_a_captured_console() -> io.StringIO:
    """``configure_logging`` without the file handler, its console handler writing into a buffer of the test."""
    configure_logging(log_level="INFO", enable_file_logging=False)
    consoles = [handler for handler in logging.getLogger().handlers if isinstance(handler, logging.StreamHandler)]
    assert len(consoles) == 1, f"setup: configure_logging must install one console handler, found {logging.getLogger().handlers}"
    buffer = io.StringIO()
    consoles[0].setStream(buffer)
    return buffer


def test_configure_logging_installs_the_filter_and_the_processor_in_place():
    """6: the filter on the console handler; ``mask_event_dict`` right after ``format_exc_info``, before the JSON renderer."""
    print_section("6: the wiring")
    with _logging_state_restored():
        configure_logging(log_level="INFO", enable_file_logging=False)
        handlers = logging.getLogger().handlers
        processors = structlog.get_config()["processors"]

        assert handlers and all(any(isinstance(log_filter, SecretMaskingFilter) for log_filter in handler.filters) for handler in handlers), f"every handler must carry the masking filter: {handlers}"
        position = processors.index(mask_event_dict)
        assert processors[position - 1] is structlog.processors.format_exc_info, "mask_event_dict must follow format_exc_info: the traceback is text by then"
        renderer = next(index for index, processor in enumerate(processors) if isinstance(processor, structlog.processors.JSONRenderer))
        assert position < renderer, "mask_event_dict must run before the JSON renderer, which would escape a secret into another text"
    print_success("filter on the handlers, processor between format_exc_info and the renderer")


def _log_everything(secret: str) -> None:
    """One line of each kind a plugin call may produce: structlog values and traceback, a library's record and traceback."""
    plugin_logger = structlog.get_logger("lf.test.secret_masking.plugin")
    library_logger = logging.getLogger("lf.test.secret_masking.library")
    plugin_logger.warning(f"provider answered for key {secret}", url=f"https://api.example/q?apikey={quote_plus(secret)}", nested={"keys": [secret]})
    try:
        raise RuntimeError(f"401 for key {secret}")
    except RuntimeError:
        plugin_logger.exception("plugin call failed")
        library_logger.exception("library request failed for %s", f"https://api.example/q?apikey={quote(secret, safe='')}")
    library_logger.warning("retrying %s", secret)


def test_every_line_of_a_call_reaches_the_handler_masked():
    """6: structlog message, values and traceback, a standard record and its traceback: masked while the secret is in flight."""
    print_section("6: the lines of a call, end to end")
    secret = _secret(" p@ss/w+rd")
    with _logging_state_restored():
        buffer = _configured_with_a_captured_console()
        with secrets_in_flight(frozenset({secret})):
            _log_everything(secret)
        inside = buffer.getvalue()

    assert inside.count("RuntimeError") >= 2, f"barrier: both tracebacks reached the handler: {inside}"
    assert not _shows(inside, secret) and _core(secret) not in inside, f"the log shows {_shows(inside, secret) or _core(secret)}:\n{inside}"
    assert inside.count(MASK) >= 7, f"every occurrence must be masked, found {inside.count(MASK)}:\n{inside}"
    print_success(f"{inside.count(MASK)} masks, no form of the secret in {len(inside.splitlines())} lines")


def test_negative_control_outside_the_block_the_same_lines_show_the_value():
    """6: the same lines without the secret in flight show it: the capture sees what a handler writes."""
    secret = _secret()
    with _logging_state_restored():
        buffer = _configured_with_a_captured_console()
        _log_everything(secret)
        outside = buffer.getvalue()

    assert secret in outside and MASK not in outside


@pytest.mark.parametrize(
    "tail",
    [pytest.param("", id="plain-ascii"), pytest.param('"q', id="a-quote"), pytest.param("\\b", id="a-backslash"), pytest.param("é", id="non-ascii")],
)
def test_a_value_that_is_no_string_reaches_the_handler_masked(tail):
    """6: an exception object as an event value, with a secret JSON would escape: no part of the secret in the line.

    The renderer writes any value that is no string as its escaped ``repr``: masked before rendering, that text is
    ``***``; left to the handler's filter, a quote, a backslash or a non-ASCII character in the secret would escape it
    into a form the filter does not search for.
    """
    secret = _secret(tail)
    with _logging_state_restored():
        buffer = _configured_with_a_captured_console()
        with secrets_in_flight(frozenset({secret})):
            structlog.get_logger("lf.test.secret_masking.plugin").warning("provider error", error=RuntimeError(f"refused {secret}"))
        line = buffer.getvalue()

    assert "provider error" in line and "refused" in line, f"barrier: the line and its value reached the handler: {line!r}"
    assert _core(secret) not in line, f"the log line shows the secret: {line!r}"
