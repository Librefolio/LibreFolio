"""
The ISO 4217 codes a currency value may stand for — lot E-19b1 (workstream E), item 1: the public candidates function.

E-18 made the write paths strict (``iso_currency_code``, ``backend/app/schemas/common.py``). E-19a (in the code) added
``suggested_iso_currency(value)``: the one ISO 4217 alphabetic code a value the old lenient rule stored stands for, or
None. Behind it, the private ``_iso_currency_candidates(code)`` takes a text already stripped and upper-cased and lists
the codes whose numeric code or name it is. A suggestion of None says nothing about *why*: no code, or two. The currency
picker of E-19b1 must tell the user which codes an ambiguous stored value could mean, so the candidates become public.

E-19b1, the contract:

``backend.app.schemas.common.iso_currency_candidates(value: Any) -> tuple[str, ...]``, the ISO 4217 alphabetic codes
``value`` may stand for:

- ``()`` for a non-string (``None``, the number ``978``…), an empty or blank text, a text past 80 characters once
  stripped, and every code of ``NEVER_RELABELLED_CURRENCY_CODES`` (GBX, ZAC, ILA) in any case;
- a valid ISO 4217 alphabetic code, in any case and with whitespace around it (NBSP included), gives ``(CODE,)``:
  ``EUR`` and ``eur`` give ``("EUR",)``, ``" GBp "`` gives ``("GBP",)``;
- otherwise the sorted alphabetic codes whose numeric code or name equals the text, case-insensitively: ``978`` and
  ``EURO`` give ``("EUR",)``, ``Bolívar Soberano`` gives ``("VED", "VES")``, ``BTC`` gives ``()``, and XXX's own
  ISO name (65 characters) gives ``("XXX",)``;
- the property: over every alphabetic code, numeric code and name pycountry lists, and every case above,
  ``suggested_iso_currency(v) == (c[0] if len(c) == 1 else None)`` where ``c = iso_currency_candidates(v)``.

One more agreement, read from E-19a rather than written in the contract: ``iso_currency_code`` names the codes of
``_iso_currency_candidates`` in its refusal. The public function must describe the same rule, so a text it accepts has
exactly one candidate, the code it stores, and a text it refuses is refused naming exactly the candidates (``… is VED or
VES``), or none (CCA-021).

The expected values of section 1 are written out: they are the contract. Sections 2 and 3 compute theirs from
``pycountry.currencies`` (every alphabetic code, numeric code and name), never from the module under test.

"RED" tests (marked ``# red until E-19b1``) fail before E-19b1: ``iso_currency_candidates`` does not exist yet. It is
looked up inside each test (``_candidates``), never at import, so the file collects and each red fails on its own,
naming what is missing. The "GUARD (green today)" test pins the pycountry data the property tests rest on.

Pure: no database, no server, no network, no file.
"""

from collections import defaultdict
from typing import Any, Callable, Optional

import pycountry
import pytest

from backend.app.schemas import common as common_module
from backend.app.schemas.common import iso_currency_code, suggested_iso_currency

# =============================================================================
# THE VALUES (the contract of E-19b1, written out)
# =============================================================================

#: The codes no value is ever relabelled to or from: pence and agorot units that are no ISO code.
NEVER_RELABELLED = frozenset({"GBX", "ZAC", "ILA"})

#: Past this many characters, once stripped, nothing is looked up.
LOOKUP_MAX_LENGTH = 80

#: A long input: nothing is looked up for it.
LONG_INPUT = "Q" * 10_000

#: XXX's own ISO name: 65 characters, the longest ISO name, within the bound.
XXX_NAME = getattr(pycountry.currencies.get(alpha_3="XXX"), "name", "")

#: The text of ``iso_currency_code``'s refusal that names its suggestion (E-19a): ``… is EUR``, ``… is VED or VES``.
REFUSAL_NAMES = "the ISO 4217 alphabetic code is {}"

#: Not a text: no candidate, and never an error. The list is unhashable: a cache keyed on the raw value must not see it.
NOT_TEXT = (None, 978, b"EUR", ["EUR"])

#: Empty, or whitespace only (NBSP included).
EMPTY_OR_BLANK = ("", " ", "   ", "\t\n", "\u00a0", "\u00a0 \t")

#: The never-relabelled codes in any case, with whitespace around them.
NEVER_RELABELLED_FORMS = ("GBX", "ZAC", "ILA", "gbx", "zac", "ila", "ZAc", "Gbx", "iLA", " gbx ", "\u00a0ila\u00a0")

#: Valid ISO 4217 alphabetic codes, in any case and padding, with the code each gives.
ISO_CODES = (("EUR", "EUR"), ("eur", "EUR"), (" EUR ", "EUR"), (" GBp ", "GBP"), ("\u00a0usd\u00a0", "USD"), ("XXX", "XXX"), ("XTS", "XTS"), ("XAU", "XAU"))

#: Numeric codes and names, in any case and padding, with the one alphabetic code each gives. The five names three
#: letters long (Yen, Lek, Som, Won, Sol) are names, not codes.
ONE_CANDIDATE = (
    ("978", "EUR"),
    (" 978 ", "EUR"),
    ("840", "USD"),
    ("999", "XXX"),
    ("963", "XTS"),
    ("008", "ALL"),
    ("EURO", "EUR"),
    ("euro", "EUR"),
    ("Euro", "EUR"),
    ("\u00a0euro\u00a0", "EUR"),
    ("US DOLLAR", "USD"),
    ("us dollar", "USD"),
    ("Pound Sterling", "GBP"),
    ("YEN", "JPY"),
    ("LEK", "ALL"),
    ("SOM", "KGS"),
    ("WON", "KRW"),
    ("SOL", "PEN"),
)

#: The name ISO 4217 gives two currencies, in any case and padding.
SEVERAL_CANDIDATES = (("Bolívar Soberano", ("VED", "VES")), ("BOLÍVAR SOBERANO", ("VED", "VES")), ("bolívar soberano", ("VED", "VES")), (" Bolívar Soberano\u00a0", ("VED", "VES")))

#: Texts that stand for no code: a crypto ticker, an unknown code, a code with spaces inside, a number no currency
#: carries (numeric codes match exactly: ``008`` is ALL's, ``8`` nothing), a name with a suffix.
NO_CANDIDATE = ("BTC", "ZZZ", "E U R", "8", "97 8", "EURO2", "Euro dollar")

#: The bound counts the stripped text: past it nothing is looked up, within it the longest ISO name is still found.
#: (value, expected, test id).
AROUND_THE_BOUND = (
    ("Q" * (LOOKUP_MAX_LENGTH + 1), (), f"{LOOKUP_MAX_LENGTH + 1}-chars"),
    (LONG_INPUT, (), "Q-x10000"),
    (XXX_NAME, ("XXX",), "XXX-own-name-65-chars"),
    (" " * 100 + "Euro" + "\u00a0" * 100, ("EUR",), "Euro-padded-to-204-chars"),
)

#: Readable test ids for the values whose text would not be.
_IDS: dict[str, str] = {
    "": "empty",
    " ": "space",
    "   ": "blank",
    "\t\n": "tab-newline",
    "\u00a0": "nbsp",
    "\u00a0 \t": "nbsp-space-tab",
    " EUR ": "spaced-EUR",
    " GBp ": "spaced-GBp",
    " gbx ": "spaced-gbx",
    " 978 ": "spaced-978",
    "\u00a0usd\u00a0": "nbsp-usd",
    "\u00a0euro\u00a0": "nbsp-euro",
    "\u00a0ila\u00a0": "nbsp-ila",
    " Bolívar Soberano\u00a0": "padded-Bolivar_Soberano",
    "Bolívar Soberano": "Bolivar_Soberano",
    "BOLÍVAR SOBERANO": "BOLIVAR_SOBERANO",
    "bolívar soberano": "bolivar_soberano",
    LONG_INPUT: "Q-x10000",
}


def _slug(value: Any) -> str:
    """The id of a value in a test name or a failure message."""
    if value is None:
        return "None"
    if isinstance(value, bytes):
        return f"bytes-{value.decode('ascii', 'replace')}"
    if isinstance(value, list):
        return f"list-{'-'.join(map(str, value))}"
    if not isinstance(value, str):
        return f"{type(value).__name__}-{value}"
    if value in _IDS:
        return _IDS[value]
    text = value.replace(" ", "_")
    return text if len(text) <= 24 else f"{text[:12]}…{len(text)}-chars"


# =============================================================================
# THE PYCOUNTRY DATA THE PROPERTY TESTS COMPUTE THEIR EXPECTATIONS FROM
# =============================================================================

#: Every currency pycountry lists, by alphabetic code.
CURRENCIES = tuple(sorted(pycountry.currencies, key=lambda currency: currency.alpha_3))
ALPHA_3 = frozenset(currency.alpha_3 for currency in CURRENCIES)


def _codes_by(key: Callable[[Any], str]) -> dict[str, tuple[str, ...]]:
    """The alphabetic codes that share each value of ``key``, sorted."""
    found: dict[str, set[str]] = defaultdict(set)
    for currency in CURRENCIES:
        found[key(currency)].add(currency.alpha_3)
    return {text: tuple(sorted(codes)) for text, codes in found.items()}


#: Numeric code → the alphabetic codes that carry it, sorted.
BY_NUMERIC = _codes_by(lambda currency: currency.numeric)
#: Upper-cased name → the alphabetic codes that carry it, sorted.
BY_NAME = _codes_by(lambda currency: currency.name.upper())


def _case_variants(text: str) -> tuple[str, ...]:
    """A text as given, upper-cased and lower-cased: the candidates compare case-insensitively."""
    return tuple(dict.fromkeys((text, text.upper(), text.lower())))


def _property_inputs() -> list[Any]:
    """Every input the property is checked on: every alphabetic code, numeric code and name pycountry lists (in their
    case variants), and every case of section 1. A list, not a set: two inputs are unhashable or of other types."""
    inputs: list[Any] = [*NOT_TEXT, *EMPTY_OR_BLANK, *NEVER_RELABELLED_FORMS, *NO_CANDIDATE]
    inputs += [value for value, _ in ISO_CODES + ONE_CANDIDATE + SEVERAL_CANDIDATES]
    inputs += [value for value, _, _ in AROUND_THE_BOUND]
    for currency in CURRENCIES:
        inputs += [*_case_variants(currency.alpha_3), currency.numeric, *_case_variants(currency.name)]
    return inputs


PROPERTY_INPUTS = _property_inputs()


# =============================================================================
# THE NEW SYMBOL, LOOKED UP WHEN A TEST RUNS (absent before E-19b1)
# =============================================================================


def _candidates() -> Callable[[Any], tuple[str, ...]]:
    """``iso_currency_candidates``, or the test fails. Looked up here, not imported, so the file collects before E-19b1."""
    function = getattr(common_module, "iso_currency_candidates", None)
    if function is None:
        pytest.fail("red until E-19b1: backend.app.schemas.common.iso_currency_candidates does not exist yet", pytrace=False)
    return function


def _candidates_with_control() -> Callable[[Any], tuple[str, ...]]:
    """``iso_currency_candidates``, once its positive control holds: ``"EUR"`` gives ``("EUR",)``, so a ``()`` elsewhere is about the input."""
    candidates = _candidates()
    assert candidates("EUR") == ("EUR",), "positive control: iso_currency_candidates('EUR') must be ('EUR',)"
    return candidates


def _accepted(value: str) -> Optional[str]:
    """The code ``iso_currency_code`` stores for ``value``, or None when it refuses it."""
    try:
        return iso_currency_code(value)
    except ValueError:
        return None


def _refusal(value: str) -> str:
    """The message of ``iso_currency_code``'s ValueError for ``value``."""
    with pytest.raises(ValueError) as refused:
        iso_currency_code(value)
    return str(refused.value)


# =============================================================================
# 1. iso_currency_candidates: what it answers
# =============================================================================


@pytest.mark.parametrize("value", [pytest.param(value, id=_slug(value)) for value in NOT_TEXT])
def test_candidates_of_a_non_string_are_none(value):  # red until E-19b1
    """CCA-001 — RED: a non-string (None, the number 978, the bytes b"EUR", the list ["EUR"]) has no candidate: ``()``, never an error."""
    assert _candidates_with_control()(value) == ()


@pytest.mark.parametrize("value", [pytest.param(value, id=_slug(value)) for value in EMPTY_OR_BLANK])
def test_candidates_of_an_empty_or_blank_text_are_none(value):  # red until E-19b1
    """CCA-002 — RED: an empty text, or one of whitespace only (NBSP included), has no candidate."""
    assert _candidates_with_control()(value) == ()


@pytest.mark.parametrize("value,expected", [pytest.param(value, expected, id=name) for value, expected, name in AROUND_THE_BOUND])
def test_candidates_look_nothing_up_past_80_characters(value, expected):  # red until E-19b1
    """CCA-003 — RED: past 80 characters once stripped, nothing is looked up: ``()``.

    Within the bound the longest ISO name is still found: XXX's own name, 65 characters, gives ``("XXX",)``. The bound
    counts the stripped text: ``Euro`` padded with 200 spaces and NBSPs is 4 characters, and gives ``("EUR",)``.
    """
    assert _candidates_with_control()(value) == expected


@pytest.mark.parametrize("value", [pytest.param(value, id=_slug(value)) for value in NEVER_RELABELLED_FORMS])
def test_candidates_never_name_gbx_zac_ila(value):  # red until E-19b1
    """CCA-004 — RED: GBX, ZAC and ILA, in any case and with whitespace around them, have no candidate: an amount in one
    is a hundredth of the unit, so no code is ever offered for them."""
    assert _candidates_with_control()(value) == ()


@pytest.mark.parametrize("value,code", [pytest.param(value, code, id=_slug(value)) for value, code in ISO_CODES])
def test_candidates_of_an_iso_code_are_itself_upper_cased(value, code):  # red until E-19b1
    """CCA-005 — RED: an ISO 4217 alphabetic code, in any case and with whitespace around it (NBSP included), gives ``(CODE,)``."""
    assert _candidates()(value) == (code,)


@pytest.mark.parametrize("value,code", [pytest.param(value, code, id=_slug(value)) for value, code in ONE_CANDIDATE])
def test_candidates_of_a_numeric_code_or_a_name(value, code):  # red until E-19b1
    """CCA-006 — RED: a numeric code or an ISO name, in any case and padding, gives the one alphabetic code that carries it.

    ``978`` and ``EURO`` give ``("EUR",)``. The five names three letters long (Yen, Lek, Som, Won, Sol) are names, not
    codes: each gives its currency's code.
    """
    assert _candidates()(value) == (code,)


@pytest.mark.parametrize("value,codes", [pytest.param(value, codes, id=_slug(value)) for value, codes in SEVERAL_CANDIDATES])
def test_candidates_of_a_name_two_currencies_share(value, codes):  # red until E-19b1
    """CCA-007 — RED: ``Bolívar Soberano``, the name of VED and of VES, gives both, sorted: ``("VED", "VES")``."""
    assert _candidates()(value) == codes


@pytest.mark.parametrize("value", [pytest.param(value, id=_slug(value)) for value in NO_CANDIDATE])
def test_candidates_of_a_text_that_stands_for_no_code(value):  # red until E-19b1
    """CCA-008 — RED: ``BTC``, ``ZZZ``, ``E U R``, ``8`` (numeric codes match exactly: ``008`` is ALL's), ``97 8``,
    ``EURO2`` and ``Euro dollar`` match nothing: ``()``."""
    assert _candidates_with_control()(value) == ()


@pytest.mark.parametrize("value", [pytest.param(XXX_NAME, id="XXX-name-as-listed"), pytest.param(XXX_NAME.upper(), id="XXX-name-upper"), pytest.param(XXX_NAME.lower(), id="XXX-name-lower")])
def test_candidates_of_xxx_own_65_character_name(value):  # red until E-19b1
    """CCA-009 — RED: XXX's own ISO name, 65 characters (as listed, upper- and lower-cased), gives ``("XXX",)``: the
    lenient rule could store it, and it is within the 80-character bound."""
    assert len(XXX_NAME) == 65, f"precondition: XXX's own name is 65 characters: {XXX_NAME!r}"
    assert _candidates()(value) == ("XXX",)


# =============================================================================
# 2. iso_currency_candidates over every ISO 4217 currency pycountry lists
# =============================================================================


def test_every_alpha_3_code_is_its_own_one_candidate():  # red until E-19b1
    """CCA-010 — RED: every alphabetic code pycountry lists gives itself alone, as listed and lower-cased."""
    candidates = _candidates()
    wrong = {text: candidates(text) for currency in CURRENCIES for text in _case_variants(currency.alpha_3) if candidates(text) != (currency.alpha_3,)}
    assert not wrong, f"{len(wrong)} alphabetic codes are not their own one candidate: {dict(list(wrong.items())[:10])}"


def test_every_numeric_code_gives_the_codes_that_carry_it():  # red until E-19b1
    """CCA-011 — RED: every numeric code pycountry lists gives the alphabetic codes that carry it, sorted."""
    candidates = _candidates()
    assert BY_NUMERIC, "precondition: pycountry lists numeric codes"
    wrong = {numeric: (candidates(numeric), expected) for numeric, expected in BY_NUMERIC.items() if candidates(numeric) != expected}
    assert not wrong, f"{len(wrong)} numeric codes give other candidates (got, expected): {dict(list(wrong.items())[:10])}"


def test_every_name_gives_the_codes_that_carry_it():  # red until E-19b1
    """CCA-012 — RED: every name pycountry lists gives the alphabetic codes that carry it, sorted, as listed, upper- and
    lower-cased: one code for most names, two for a name ISO 4217 gives two currencies."""
    candidates = _candidates()
    wrong = {text: (candidates(text), BY_NAME[currency.name.upper()]) for currency in CURRENCIES for text in _case_variants(currency.name) if candidates(text) != BY_NAME[currency.name.upper()]}
    assert not wrong, f"{len(wrong)} names give other candidates (got, expected): {dict(list(wrong.items())[:10])}"


def test_candidates_are_always_a_sorted_tuple_of_distinct_iso_codes():  # red until E-19b1
    """CCA-013 — RED: over every input of the property table, the answer is a tuple of distinct ISO 4217 alphabetic
    codes, in sorted order (possibly empty)."""
    candidates = _candidates()
    wrong = []
    for value in PROPERTY_INPUTS:
        found = candidates(value)
        if not isinstance(found, tuple) or not all(isinstance(code, str) for code in found) or list(found) != sorted(set(found)) or not set(found) <= ALPHA_3:
            wrong.append((_slug(value), found))
    assert not wrong, f"{len(wrong)} answers are not a sorted tuple of distinct ISO codes: {wrong[:10]}"


# =============================================================================
# 3. The candidates agree with the suggestion and with the strict rule
# =============================================================================


def test_the_suggestion_is_the_one_candidate_or_none():  # red until E-19b1
    """CCA-020 — RED: the contract's property. Over every alphabetic code, numeric code and name pycountry lists (in
    their case variants) and every case of section 1, ``suggested_iso_currency(v)`` is the candidate when there is
    exactly one, None otherwise."""
    candidates = _candidates()
    assert len(PROPERTY_INPUTS) > 3 * len(CURRENCIES), f"precondition: the table holds every code, numeric code and name: {len(PROPERTY_INPUTS)} inputs"
    wrong = []
    for value in PROPERTY_INPUTS:
        found = candidates(value)
        expected = found[0] if len(found) == 1 else None
        suggested = suggested_iso_currency(value)
        if suggested != expected:
            wrong.append((_slug(value), found, suggested))
    assert not wrong, f"{len(wrong)} inputs whose suggestion is not their one candidate (value, candidates, suggestion): {wrong[:10]}"


def test_the_strict_rule_names_exactly_the_candidates():  # red until E-19b1
    """CCA-021 — RED: ``iso_currency_code`` and the candidates describe one rule. Over every text of the property table:

    - a text it accepts has exactly one candidate, the code it stores;
    - a text it refuses with a suggestion is refused naming exactly the candidates, sorted, joined by `` or ``
      (``… the ISO 4217 alphabetic code is VED or VES``);
    - a text it refuses naming no code has no candidate.
    """
    candidates = _candidates()
    texts = [value for value in PROPERTY_INPUTS if isinstance(value, str)]
    wrong = []
    for value in texts:
        found = candidates(value)
        stored = _accepted(value)
        if stored is not None:
            if found != (stored,):
                wrong.append((_slug(value), found, f"accepted as {stored}"))
            continue
        message = _refusal(value)
        named = message.endswith(REFUSAL_NAMES.format(" or ".join(found))) if found else "alphabetic code is" not in message
        if not named:
            wrong.append((_slug(value), found, message[:120]))
    assert not wrong, f"{len(wrong)} texts on which iso_currency_code and the candidates disagree (value, candidates, verdict): {wrong[:10]}"


# =============================================================================
# 4. The data the property tests rest on
# =============================================================================


def test_pycountry_data_the_properties_rest_on():
    """CCA-030 — GUARD (green today): the pycountry data sections 2 and 3 compute from has the shape they assume.

    - Every currency has a three-letter upper-case ASCII code and a three-digit numeric code.
    - No name is an alphabetic code, or "a code gives itself" would hide the name rule.
    - GBX, ZAC and ILA are no ISO code, or "never relabelled" would contradict "every code gives itself".
    - Bolívar Soberano is the name of VED and of VES: the ambiguous case exists.
    - Every name fits within the 80-character bound; the longest is XXX's, 65 characters.
    - ``8`` is no numeric code, while ``008`` is ALL's.
    """
    assert len(CURRENCIES) >= 150, f"pycountry lists only {len(CURRENCIES)} currencies"
    assert all(len(code) == 3 and code.isascii() and code.isalpha() and code.isupper() for code in ALPHA_3)
    assert all(len(numeric) == 3 and numeric.isdigit() for numeric in BY_NUMERIC)
    assert not set(BY_NAME) & ALPHA_3, f"names that are alphabetic codes: {set(BY_NAME) & ALPHA_3}"
    assert not NEVER_RELABELLED & ALPHA_3, f"never-relabelled codes that ISO lists: {NEVER_RELABELLED & ALPHA_3}"
    assert BY_NAME.get("BOLÍVAR SOBERANO") == ("VED", "VES")
    longest = max(CURRENCIES, key=lambda currency: len(currency.name))
    assert (longest.alpha_3, len(longest.name)) == ("XXX", 65), f"the longest name is {longest.alpha_3}'s, {len(longest.name)} characters: {longest.name!r}"
    assert len(longest.name) <= LOOKUP_MAX_LENGTH
    assert ("8" not in BY_NUMERIC, BY_NUMERIC.get("008")) == (True, ("ALL",))
