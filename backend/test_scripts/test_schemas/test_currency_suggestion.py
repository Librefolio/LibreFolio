"""
A suggested ISO 4217 code, and refusals that name it — lot E-19a (workstream E), items 1 to 3.

E-18 made the write paths strict: ``iso_currency_code`` (``backend/app/schemas/common.py``) strips the text (NBSP
included), upper-cases it and accepts only three ASCII letters that pycountry lists as an ISO 4217 alphabetic code. It
refuses anything else with ``Invalid currency code '<shown>': expected an ISO 4217 alphabetic code, such as EUR``,
quoting at most 16 characters of the text (``_REFUSED_CURRENCY_SHOWN``). The old lenient rule (``Currency.validate_code``,
still on the read paths) took an ISO name or a numeric code and stored it as given, so databases can hold ``EURO``,
``978``, ``US DOLLAR`` or ``YEN``. Refusing them is right, but the refusal does not say what to write instead.

E-19a, as the release coordinator decided on 17/10:

1. ``backend.app.schemas.common.suggested_iso_currency(value) -> Optional[str]``:
   - ``None`` for a non-string, an empty or blank text, a text longer than 80 characters once stripped (nothing is
     looked up then: every ISO name is at most 65 characters, so XXX's own name is still found), and the codes of ``NEVER_RELABELLED_CURRENCY_CODES`` (``frozenset({"GBX", "ZAC", "ILA"})``) in any
     case;
   - the text is stripped (NBSP included) and upper-cased, and an ISO 4217 alphabetic code gives itself;
   - otherwise the alphabetic codes whose numeric code or name equals the text, case-insensitively: exactly one distinct
     code gives that code, none or several give ``None``.
2. ``iso_currency_code`` keeps its rule and its 16-character bound, and its refusal names the suggestion: it ends with
   ``the ISO 4217 alphabetic code is <CODE>``, or ``… is VED or VES`` for several (sorted, joined by `` or ``). With no
   suggestion it says ``expected an ISO 4217 alphabetic code`` and ``such as EUR or USD``.
3. The user's base currency becomes strict: ``UserSettingsUpdate.base_currency`` and
   ``OnboardingWelcomeSettings.base_currency`` take the ``iso_currency_code`` rule and keep their JSON schema (a string
   of 3 characters, optional in the update).

The expected values are written out here, not computed from the module: they are the contract. The property tests
(section 2) compute theirs from ``pycountry.currencies`` (every alphabetic code, numeric code and name), never from the
module under test.

"RED" tests (marked ``# red until E-19a``) fail before E-19a. ``suggested_iso_currency`` and
``NEVER_RELABELLED_CURRENCY_CODES`` do not exist yet: they are looked up inside each test, so the file collects and each
red fails on its own. The refusal names no suggestion, and the settings accept any three characters. "GUARD (green
today)" tests pass before and after: what E-18 guarantees of every refusal, what the settings already do and keep, and
the pycountry data the property tests rest on.

Pure: no database, no server, no network, no file.
"""

import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Callable, Optional

import pycountry
import pytest
from pydantic import BaseModel, TypeAdapter, ValidationError

from backend.app.schemas import common as common_module
from backend.app.schemas.common import iso_currency_code
from backend.app.schemas.settings import OnboardingWelcomeSettings, UserSettingsUpdate

# =============================================================================
# THE VALUES (the contract of 17/10, written out)
# =============================================================================

#: The codes a suggestion never relabels: pence and agorot units that are no ISO code (GBX, ZAC, ILA).
NEVER_RELABELLED = frozenset({"GBX", "ZAC", "ILA"})

#: Past this many characters, once stripped, the suggestion looks nothing up.
SUGGESTION_MAX_LENGTH = 80

#: How many characters of a refused text a refusal quotes (E-18, ``_REFUSED_CURRENCY_SHOWN``).
SHOWN = 16

#: What a refusal with exactly one suggestion ends with.
ENDS_WITH_CODE = "the ISO 4217 alphabetic code is {}"

#: The generic example of a refusal without a suggestion. A refusal that "names EUR" names it outside this example.
GENERIC_EXAMPLE = "such as EUR or USD"

#: A long input: the refusal must not echo it, and the suggestion must not look it up.
LONG_INPUT = "Q" * 10_000

#: Readable test ids for the values whose text would not be.
_IDS: dict[Any, str] = {
    "": "empty",
    " ": "space",
    "   ": "blank",
    "\t\n": "tab-newline",
    "\u00a0": "nbsp",
    "\u00a0 \t": "nbsp-space-tab",
    " EUR ": "spaced-EUR",
    "\u00a0usd\u00a0": "nbsp-usd",
    "\u00a0euro\u00a0": "nbsp-euro",
    " gbx ": "spaced-gbx",
    " usd ": "spaced-usd",
    "\u00a0gbp\u00a0": "nbsp-gbp",
    " us dollar ": "spaced-us-dollar",
    LONG_INPUT: "Q-x10000",
    None: "None",
    978: "int-978",
    b"EUR": "bytes-EUR",
}


def _slug(value: Any) -> str:
    """The id of a value in a test name."""
    if value in _IDS:
        return _IDS[value]
    text = str(value).replace(" ", "_")
    return text if len(text) <= 24 else f"{text[:12]}…{len(text)}-chars"


# =============================================================================
# THE PYCOUNTRY DATA THE PROPERTY TESTS COMPUTE THEIR EXPECTATIONS FROM
# =============================================================================

#: Every currency pycountry lists, by alphabetic code.
CURRENCIES = tuple(sorted(pycountry.currencies, key=lambda currency: currency.alpha_3))


def _codes_by(key: Callable[[Any], str]) -> dict[str, frozenset[str]]:
    """The alphabetic codes that share each value of ``key``."""
    found: dict[str, set[str]] = defaultdict(set)
    for currency in CURRENCIES:
        found[key(currency)].add(currency.alpha_3)
    return {text: frozenset(codes) for text, codes in found.items()}


#: Numeric code → the alphabetic codes that carry it.
BY_NUMERIC = _codes_by(lambda currency: currency.numeric)
#: Upper-cased name → the alphabetic codes that carry it.
BY_NAME = _codes_by(lambda currency: currency.name.upper())
#: XXX's own ISO name: 65 characters, the longest ISO name, within the bound. The lenient rule could store it.
XXX_NAME = getattr(pycountry.currencies.get(alpha_3="XXX"), "name", "")


def _case_variants(text: str) -> tuple[str, ...]:
    """A text as given, upper-cased and lower-cased: the suggestion compares case-insensitively."""
    return tuple(dict.fromkeys((text, text.upper(), text.lower())))


# =============================================================================
# THE NEW SYMBOLS, LOOKED UP WHEN A TEST RUNS (absent before E-19a)
# =============================================================================


def _suggest() -> Callable[[Any], Optional[str]]:
    """``suggested_iso_currency``, or the test fails. Looked up here, not imported, so the file collects before E-19a."""
    function = getattr(common_module, "suggested_iso_currency", None)
    if function is None:
        pytest.fail("red until E-19a: backend.app.schemas.common.suggested_iso_currency does not exist yet", pytrace=False)
    return function


def _suggest_with_control() -> Callable[[Any], Optional[str]]:
    """``suggested_iso_currency``, once its positive control holds: ``"EUR"`` gives ``"EUR"``, so a ``None`` elsewhere is about the input."""
    suggest = _suggest()
    assert suggest("EUR") == "EUR", "positive control: suggested_iso_currency('EUR') must be 'EUR'"
    return suggest


def _refusal(value: Any) -> str:
    """The message of ``iso_currency_code``'s ValueError for ``value``."""
    with pytest.raises(ValueError) as refused:
        iso_currency_code(value)
    return str(refused.value)


def _shown(value: str) -> str:
    """The refused text as a refusal sees it: stripped (NBSP included) and upper-cased."""
    return value.strip().upper()


def _quote_problem(message: str, value: str) -> Optional[str]:
    """``None`` when ``message`` quotes the refused text and echoes at most 16 characters of it; otherwise what is wrong."""
    shown = _shown(value)
    if len(shown) <= SHOWN:
        return None if f"'{shown}'" in message else f"the refusal must quote the refused text as {shown!r}: {message!r}"
    if shown[: SHOWN + 1] in message:
        return f"the refusal echoes more than {SHOWN} characters of the refused text ({len(message)} characters): {message[:120]!r}…"
    if "'" + shown[:SHOWN] not in message:
        return f"the refusal must quote the first {SHOWN} characters of the refused text, {shown[:SHOWN]!r}: {message[:120]!r}"
    return None


def _names_as_suggestion(message: str, code: str) -> bool:
    """``code`` appears in ``message`` as a code of its own, outside the generic example ``such as EUR or USD``."""
    return re.search(rf"(?<![A-Z]){code}(?![A-Z])", message.replace(GENERIC_EXAMPLE, "")) is not None


# =============================================================================
# 1. suggested_iso_currency: what it answers
# =============================================================================


def test_never_relabelled_codes_are_exactly_gbx_zac_ila():  # red until E-19a
    """CSG-001 — RED: ``NEVER_RELABELLED_CURRENCY_CODES`` is the frozenset ``{"GBX", "ZAC", "ILA"}``."""
    found = getattr(common_module, "NEVER_RELABELLED_CURRENCY_CODES", None)
    if found is None:
        pytest.fail("red until E-19a: backend.app.schemas.common.NEVER_RELABELLED_CURRENCY_CODES does not exist yet", pytrace=False)
    assert isinstance(found, frozenset), f"NEVER_RELABELLED_CURRENCY_CODES must be a frozenset (immutable), got {type(found).__name__}"
    assert found == NEVER_RELABELLED


@pytest.mark.parametrize("value", [pytest.param(value, id=_slug(value)) for value in (None, 978, b"EUR")])
def test_suggestion_of_a_non_string_is_none(value):  # red until E-19a
    """CSG-002 — RED: a non-string (None, the number 978, the bytes b"EUR") has no suggestion: None, never an error."""
    assert _suggest_with_control()(value) is None


@pytest.mark.parametrize("value", [pytest.param(value, id=_slug(value)) for value in ("", " ", "\t\n", "\u00a0", "\u00a0 \t")])
def test_suggestion_of_an_empty_or_blank_text_is_none(value):  # red until E-19a
    """CSG-003 — RED: an empty text, or one of whitespace only (NBSP included), has no suggestion."""
    assert _suggest_with_control()(value) is None


@pytest.mark.parametrize(
    "value,expected",
    [
        pytest.param("Q" * (SUGGESTION_MAX_LENGTH + 1), None, id=f"{SUGGESTION_MAX_LENGTH + 1}-chars"),
        pytest.param(LONG_INPUT, None, id="Q-x10000"),
        pytest.param(XXX_NAME, "XXX", id="XXX-own-name-65-chars"),
        pytest.param(" " * 100 + "Euro" + "\u00a0" * 100, "EUR", id="Euro-padded-to-204-chars"),
    ],
)
def test_suggestion_looks_nothing_up_past_80_characters(value, expected):  # red until E-19a
    """CSG-004 — RED: past 80 characters once stripped, nothing is looked up: None.

    Within the bound, the longest ISO name is still found: XXX's own name, 65 characters, gives XXX (the lenient rule
    could store it). The bound counts the stripped text: ``Euro`` padded with 200 spaces and NBSPs is 4 characters, and
    gives EUR.
    """
    assert _suggest_with_control()(value) == expected


@pytest.mark.parametrize("value", [pytest.param(value, id=_slug(value)) for value in ("GBX", "ZAC", "ILA", "zac", "ZAc", "Gbx", "ila", " gbx ")])
def test_suggestion_never_relabels_gbx_zac_ila(value):  # red until E-19a
    """CSG-005 — RED: GBX, ZAC and ILA, in any case and with whitespace around them, have no suggestion."""
    assert _suggest_with_control()(value) is None


@pytest.mark.parametrize(
    "value,expected",
    [pytest.param(value, expected, id=_slug(value)) for value, expected in (("EUR", "EUR"), ("eur", "EUR"), (" EUR ", "EUR"), ("\u00a0usd\u00a0", "USD"), ("GBp", "GBP"), ("XXX", "XXX"), ("XTS", "XTS"))],
)
def test_suggestion_of_an_iso_code_is_itself_upper_cased(value, expected):  # red until E-19a
    """CSG-006 — RED: an ISO 4217 alphabetic code, in any case and with whitespace around it (NBSP included), gives itself upper-cased."""
    assert _suggest()(value) == expected


#: Numeric codes and names, with the one alphabetic code each gives.
BY_NUMBER_OR_NAME = (
    ("978", "EUR"),
    ("840", "USD"),
    ("999", "XXX"),
    ("963", "XTS"),
    ("008", "ALL"),
    ("EURO", "EUR"),
    ("euro", "EUR"),
    ("\u00a0euro\u00a0", "EUR"),
    ("US DOLLAR", "USD"),
    ("Pound Sterling", "GBP"),
    ("YEN", "JPY"),
    ("LEK", "ALL"),
    ("SOM", "KGS"),
    ("WON", "KRW"),
    ("SOL", "PEN"),
)


@pytest.mark.parametrize("value,expected", [pytest.param(value, expected, id=_slug(value)) for value, expected in BY_NUMBER_OR_NAME])
def test_suggestion_of_a_numeric_code_or_a_name(value, expected):  # red until E-19a
    """CSG-007 — RED: a numeric code or an ISO name, in any case, gives the one alphabetic code that carries it.

    The five names three letters long (Lek, Yen, Som, Won, Sol) are names, not codes: each gives its currency's code.
    """
    assert _suggest()(value) == expected


@pytest.mark.parametrize("value", [pytest.param(value, id=_slug(value)) for value in ("Bolívar Soberano", "BOLÍVAR SOBERANO", "bolívar soberano", "BTC", "8", "ZZZ", "E U R")])
def test_suggestion_of_an_ambiguous_or_unknown_text_is_none(value):  # red until E-19a
    """CSG-008 — RED: none or several codes give None.

    ``Bolívar Soberano`` is the name of both VED and VES. ``BTC``, ``ZZZ`` and ``E U R`` match nothing. ``8`` is no
    numeric code: they match exactly, and ``008`` is ALL's.
    """
    assert _suggest_with_control()(value) is None


# =============================================================================
# 2. suggested_iso_currency over every ISO 4217 currency pycountry lists
# =============================================================================


def test_every_alpha_3_code_suggests_itself():  # red until E-19a
    """CSG-010 — RED: every alphabetic code pycountry lists gives itself, as listed and lower-cased."""
    suggest = _suggest()
    wrong = {text: suggest(text) for currency in CURRENCIES for text in _case_variants(currency.alpha_3) if suggest(text) != currency.alpha_3}
    assert not wrong, f"{len(wrong)} alphabetic codes do not suggest themselves: {dict(list(wrong.items())[:10])}"


def test_every_unshared_numeric_code_suggests_its_alpha_3():  # red until E-19a
    """CSG-011 — RED: every numeric code that no other currency shares gives its alphabetic code."""
    suggest = _suggest()
    unshared = {numeric: next(iter(codes)) for numeric, codes in BY_NUMERIC.items() if len(codes) == 1}
    assert unshared, "precondition: pycountry lists numeric codes"
    wrong = {numeric: (suggest(numeric), expected) for numeric, expected in unshared.items() if suggest(numeric) != expected}
    assert not wrong, f"{len(wrong)} numeric codes do not suggest their alphabetic code (got, expected): {dict(list(wrong.items())[:10])}"


def test_every_unshared_name_suggests_its_alpha_3():  # red until E-19a
    """CSG-012 — RED: every name that no other currency shares gives its alphabetic code, as listed, upper- and lower-cased.

    Every one, the longest included: XXX's own name, 65 characters.
    """
    suggest = _suggest()
    unshared = [(currency.name, currency.alpha_3) for currency in CURRENCIES if len(BY_NAME[currency.name.upper()]) == 1]
    assert (XXX_NAME, "XXX") in unshared, f"precondition: XXX's own name is among the unshared names checked: {XXX_NAME!r}"
    wrong = {text: (suggest(text), code) for name, code in unshared for text in _case_variants(name) if suggest(text) != code}
    assert not wrong, f"{len(wrong)} names do not suggest their alphabetic code (got, expected): {dict(list(wrong.items())[:10])}"


def test_every_shared_name_suggests_nothing():  # red until E-19a
    """CSG-013 — RED: a name that several currencies share gives None, as listed, upper- and lower-cased."""
    suggest = _suggest_with_control()
    shared = sorted({currency.name for currency in CURRENCIES if len(BY_NAME[currency.name.upper()]) > 1})
    assert shared, "precondition: pycountry lists at least one name shared by several currencies"
    wrong = {text: suggest(text) for name in shared for text in _case_variants(name) if suggest(text) is not None}
    assert not wrong, f"shared names must suggest nothing: {wrong}"


def test_pycountry_data_the_properties_rest_on():
    """CSG-014 — GUARD (green today): the pycountry data the property tests compute from has the shape they assume.

    - Every currency has a three-letter upper-case ASCII code and a three-digit numeric code, and no two share the code.
    - No name is an alphabetic code, or the "a code gives itself" rule would hide the name rule.
    - GBX, ZAC and ILA are no ISO code, or "never relabelled" would contradict "every code gives itself".
    - Bolívar Soberano is the name of VED and of VES.
    - Every name fits within the 80-character bound; the longest is XXX's, 65 characters.
    - ``8`` is no numeric code, while ``008`` is ALL's.
    """
    alpha_3 = [currency.alpha_3 for currency in CURRENCIES]
    assert len(CURRENCIES) >= 150, f"pycountry lists only {len(CURRENCIES)} currencies"
    assert all(len(code) == 3 and code.isascii() and code.isalpha() and code.isupper() for code in alpha_3)
    assert len(set(alpha_3)) == len(alpha_3), "an alphabetic code is listed twice"
    assert all(len(numeric) == 3 and numeric.isdigit() for numeric in BY_NUMERIC)
    assert not set(BY_NAME) & set(alpha_3), f"names that are alphabetic codes: {set(BY_NAME) & set(alpha_3)}"
    assert not NEVER_RELABELLED & set(alpha_3), f"never-relabelled codes that ISO lists: {NEVER_RELABELLED & set(alpha_3)}"
    assert BY_NAME.get("BOLÍVAR SOBERANO") == frozenset({"VED", "VES"})
    longest = max(CURRENCIES, key=lambda currency: len(currency.name))
    assert (longest.alpha_3, len(longest.name)) == ("XXX", 65), f"the longest name is {longest.alpha_3}'s, {len(longest.name)} characters: {longest.name!r}"
    assert len(longest.name) <= SUGGESTION_MAX_LENGTH, f"a name of {len(longest.name)} characters is past the {SUGGESTION_MAX_LENGTH}-character bound"
    assert ("8" not in BY_NUMERIC, BY_NUMERIC.get("008")) == (True, frozenset({"ALL"}))


# =============================================================================
# 3. The refusal of iso_currency_code names the suggestion
# =============================================================================

#: Refused texts with exactly one suggestion, and the code their refusal ends on. "Australian Dollar" is 17 characters:
#: the suggestion reads all of them, the refusal quotes 16.
ONE_SUGGESTION = (("840", "USD"), ("978", "EUR"), ("EURO", "EUR"), ("us dollar", "USD"), (" us dollar ", "USD"), ("Australian Dollar", "AUD"))

#: Refused texts with several suggestions, and how their refusal names them: sorted, joined by " or ".
SEVERAL_SUGGESTIONS = (("Bolívar Soberano", "VED or VES"), ("bolívar soberano", "VED or VES"))

#: Refused texts with no suggestion at all.
NO_SUGGESTION = ("GBX", "BTC", "ZAC", "", "   ", LONG_INPUT)


@pytest.mark.parametrize("value,code", [pytest.param(value, code, id=_slug(value)) for value, code in ONE_SUGGESTION])
def test_refusal_ends_with_the_one_suggestion(value, code):  # red until E-19a
    """CSG-020 — RED: a refused text with one suggestion is refused with a message ending ``the ISO 4217 alphabetic code is <CODE>``.

    ``us dollar`` is quoted upper-cased, as ``'US DOLLAR'``; ``Australian Dollar`` as its first 16 characters.
    """
    message = _refusal(value)
    expected_end = ENDS_WITH_CODE.format(code)
    if not message.endswith(expected_end):
        pytest.fail(f"red until E-19a: the refusal of {value!r} must end with {expected_end!r}; it is {message!r}", pytrace=False)
    assert _quote_problem(message, value) is None, _quote_problem(message, value)


@pytest.mark.parametrize("value,codes", [pytest.param(value, codes, id=_slug(value)) for value, codes in SEVERAL_SUGGESTIONS])
def test_refusal_names_every_code_of_an_ambiguous_name(value, codes):  # red until E-19a
    """CSG-021 — RED: ``Bolívar Soberano``, the name of VED and VES, is refused with a message ending ``the ISO 4217 alphabetic code is VED or VES``."""
    message = _refusal(value)
    expected_end = ENDS_WITH_CODE.format(codes)
    if not message.endswith(expected_end):
        pytest.fail(f"red until E-19a: the refusal of {value!r} must end with {expected_end!r}; it is {message!r}", pytrace=False)
    assert _quote_problem(message, value) is None, _quote_problem(message, value)


@pytest.mark.parametrize("value", [pytest.param(value, id=_slug(value)) for value in NO_SUGGESTION])
def test_refusal_without_a_suggestion_gives_two_examples(value):  # red until E-19a
    """CSG-022 — RED: a refused text with no suggestion (GBX, BTC, ZAC, empty, blank, 10 000 characters) is refused with a
    message saying ``expected an ISO 4217 alphabetic code`` and ``such as EUR or USD``, and naming no code as *the* code."""
    message = _refusal(value)
    missing = [part for part in ("expected an ISO 4217 alphabetic code", GENERIC_EXAMPLE) if part not in message]
    if missing:
        pytest.fail(f"red until E-19a: the refusal of {_slug(value)!r} must say {missing}; it is {message[:200]!r}", pytrace=False)
    assert "alphabetic code is" not in message, f"no code suggested, so the refusal names none: {message[:200]!r}"
    assert _quote_problem(message, value) is None, _quote_problem(message, value)


@pytest.mark.parametrize("value", [pytest.param(value, id=_slug(value)) for value in dict.fromkeys([value for value, _ in ONE_SUGGESTION + SEVERAL_SUGGESTIONS] + list(NO_SUGGESTION))])
def test_every_refusal_names_the_rule_and_quotes_at_most_16_characters(value):
    """CSG-023 — GUARD (green today): every refusal names ``ISO 4217`` and quotes the refused text, upper-cased, never more than 16 characters of it (E-18)."""
    message = _refusal(value)
    assert "ISO 4217" in message, message[:200]
    assert _quote_problem(message, value) is None, _quote_problem(message, value)


def test_refusal_through_the_annotated_type_carries_the_same_text():  # red until E-19a
    """CSG-024 — RED: through ``TypeAdapter(IsoCurrencyCode)``, ``'840'`` is a ValidationError whose msg carries the
    function's own message, ending ``the ISO 4217 alphabetic code is USD``."""
    message = _refusal("840")
    with pytest.raises(ValidationError) as refused:
        TypeAdapter(common_module.IsoCurrencyCode).validate_python("840")
    messages = [error["msg"] for error in refused.value.errors()]
    assert len(messages) == 1 and message in messages[0], f"the msg must carry {message!r}: {messages}"
    expected_end = ENDS_WITH_CODE.format("USD")
    if not messages[0].endswith(expected_end):
        pytest.fail(f"red until E-19a: the msg must end with {expected_end!r}; it is {messages[0]!r}", pytrace=False)


# =============================================================================
# 4. The user's base currency: strict, with the same JSON schema
# =============================================================================


@dataclass(frozen=True)
class SettingsSite:
    """A base-currency field of the settings: its model built around one code."""

    name: str
    build: Callable[[Any], BaseModel]


SETTINGS_SITES = (
    SettingsSite("UserSettingsUpdate", lambda code: UserSettingsUpdate(base_currency=code)),
    SettingsSite("OnboardingWelcomeSettings", lambda code: OnboardingWelcomeSettings(language="en", base_currency=code)),
)

#: Three characters that are no ISO 4217 alphabetic code: an unknown code, then E-18's lenient forms (numeric codes and
#: the five ISO names three letters long). The settings' length check passes them all today.
SETTINGS_REFUSES = ("XYZ", "978", "999", "YEN", "LEK", "SOM", "WON", "SOL")

#: Accepted, and stored upper-cased.
SETTINGS_ACCEPTS = (("eur", "EUR"), (" usd ", "USD"), ("\u00a0gbp\u00a0", "GBP"))


def _settings_positive_control(site: SettingsSite) -> None:
    """The same model with ``"EUR"`` validates and holds ``"EUR"``: a refusal of another code is about that code alone."""
    held = site.build("EUR").base_currency
    assert held == "EUR", f"positive control: {site.name} holds {held!r} for 'EUR'"


def _settings_refusal(site: SettingsSite, value: Any) -> list[dict[str, Any]]:
    """The errors of ``site`` refusing ``value``; the test fails, red, when it is accepted."""
    _settings_positive_control(site)
    try:
        item = site.build(value)
    except ValidationError as refused:
        return refused.errors()
    pytest.fail(f"red until E-19a: {site.name} accepted the base currency {value!r} and holds {item.base_currency!r}", pytrace=False)


@pytest.mark.parametrize("site", [pytest.param(site, id=site.name) for site in SETTINGS_SITES])
def test_settings_refuse_a_numeric_code_naming_eur(site):  # red until E-19a
    """CSG-030 — RED: a base currency of ``978`` is a ValidationError on ``base_currency`` whose message names ``ISO 4217`` and ``EUR``.

    ``EUR`` must be named as the suggestion, not only inside the generic example ``such as EUR or USD``.
    """
    errors = _settings_refusal(site, "978")
    assert [error["loc"] for error in errors] == [("base_currency",)], errors
    message = errors[0]["msg"]
    assert "ISO 4217" in message, message
    assert _names_as_suggestion(message, "EUR"), f"the refusal of '978' must name EUR, its ISO code: {message!r}"


@pytest.mark.parametrize("site,value", [pytest.param(site, value, id=f"{site.name}-{value}") for site in SETTINGS_SITES for value in SETTINGS_REFUSES])
def test_settings_refuse_what_is_no_iso_code(site, value):  # red until E-19a
    """CSG-031 — RED: an unknown code (``XYZ``) or a lenient form three characters long (``978``, ``999``, ``YEN``…) is a ValidationError on ``base_currency``."""
    errors = _settings_refusal(site, value)
    assert [error["loc"] for error in errors] == [("base_currency",)], errors


@pytest.mark.parametrize("site,value,expected", [pytest.param(site, value, expected, id=f"{site.name}-{_slug(value)}") for site in SETTINGS_SITES for value, expected in SETTINGS_ACCEPTS])
def test_settings_accept_and_upper_case_an_iso_code(site, value, expected):  # red until E-19a
    """CSG-032 — RED: ``eur``, `` usd `` and ``\\u00a0gbp\\u00a0`` are held as ``EUR``, ``USD`` and ``GBP``, in the model and its dump.

    The whitespace is stripped before the three-character length is checked.
    """
    try:
        item = site.build(value)
    except ValidationError as refused:
        pytest.fail(f"red until E-19a: {site.name} refuses the base currency {value!r}: {[error['msg'] for error in refused.errors()]}", pytrace=False)
    if item.base_currency != expected:
        pytest.fail(f"red until E-19a: {site.name} holds {item.base_currency!r} for {value!r}, not {expected!r}", pytrace=False)
    assert item.model_dump()["base_currency"] == expected


@pytest.mark.parametrize("site,value", [pytest.param(site, value, id=f"{site.name}-{value}") for site in SETTINGS_SITES for value in ("EUR", "USD", "CHF", "XAU")])
def test_settings_keep_a_canonical_code_unchanged(site, value):
    """CSG-033 — GUARD (green today): an ISO 4217 alphabetic code already upper-case is held as given."""
    assert site.build(value).base_currency == value


def test_settings_update_without_a_base_currency_holds_none():
    """CSG-034 — GUARD (green today): ``UserSettingsUpdate()`` and ``UserSettingsUpdate(base_currency=None)`` hold None: the field stays optional."""
    assert (UserSettingsUpdate().base_currency, UserSettingsUpdate(base_currency=None).base_currency) == (None, None)


def _string_schema(model: type[BaseModel], optional: bool) -> dict[str, Any]:
    """The JSON schema of ``model.base_currency`` as a string: its own, or the string branch of the ``anyOf`` of an Optional."""
    schema = model.model_json_schema()["properties"]["base_currency"]
    if not optional:
        assert "anyOf" not in schema, f"{model.__name__}.base_currency is required, not optional: {schema}"
        return schema
    branches = schema.get("anyOf", [])
    assert {"type": "null"} in branches, f"{model.__name__}.base_currency must stay optional (a null branch): {schema}"
    strings = [branch for branch in branches if branch.get("type") == "string"]
    assert len(strings) == 1, f"{model.__name__}.base_currency must have one string branch: {schema}"
    return strings[0]


@pytest.mark.parametrize("model,optional", [pytest.param(UserSettingsUpdate, True, id="UserSettingsUpdate"), pytest.param(OnboardingWelcomeSettings, False, id="OnboardingWelcomeSettings")])
def test_settings_json_schema_is_unchanged(model, optional):
    """CSG-035 — GUARD (green today): the JSON schema of ``base_currency`` stays a string of exactly 3 characters (minLength 3, maxLength 3), optional in the update.

    The generated frontend client reads it: a strict rule must not change the wire contract.
    """
    schema = _string_schema(model, optional)
    assert (schema.get("type"), schema.get("minLength"), schema.get("maxLength")) == ("string", 3, 3), schema
