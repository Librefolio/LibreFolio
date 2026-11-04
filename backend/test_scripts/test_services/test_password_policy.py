"""``password_policy``: the password rules in one place, the backend (release 1.3, workstream A, lot A6c — decision 37).

Until 1.3 the five rules were written twice, and the two copies disagreed: ``scripts/user_cli.py`` ``validate_password``
(``str.isupper``, ``str.islower``, ``str.isdigit`` and a fixed set of ASCII symbols) and the frontend's
``PasswordStrength.svelte`` (ASCII regular expressions, another set of symbols), while the API asked for eight characters
and nothing else. Decision 37 of the developer: the rules live in the backend, which applies them to every new password
and publishes them. C1 of the approved contract, pinned here:

1. ``backend/app/services/accounts/password_policy.py`` holds today's five rules, in this order: ``min_length`` (value
   8), ``uppercase``, ``lowercase``, ``digit``, ``special``.
2. ``failed_rules(password: str) -> list[str]`` answers the codes of the rules the password does not meet, in that
   order, whatever order the password shows them in: ``[]`` when it meets every rule, all five for the empty password.
3. The character classes are Unicode's (the coordinator's night decision, approved «to review»): an uppercase letter is
   a character of category ``Lu``, a lowercase letter ``Ll``, a digit ``Nd``; a symbol (``special``) is any character
   that is neither a letter (``L*``), nor a number (``N*``), nor whitespace. The length counts characters — code points,
   ``len()`` of the password as given —, not UTF-8 bytes nor UTF-16 units. So ``É`` is an uppercase letter and ``é`` a
   lowercase one, ``٣`` (Arabic-Indic three) a digit, ``€`` and ``_`` symbols; a space is not a symbol, and ``ü`` is a
   letter, not a symbol. Where the categories and the ``str`` methods of the old command-line copy part ways, the
   category decides: ``²`` is a number but not a digit, ``Ⓐ`` a symbol but not an uppercase letter, ``ª`` a letter but
   not a lowercase one (POLICY-006, the part of the night decision under review).
4. ``password_rules_public`` — a function, or a constant of that name — is what ``GET /system/instance`` publishes as
   ``accounts.password_rules``: ``[{"code": "min_length", "value": 8}, {"code": "uppercase"}, {"code": "lowercase"},
   {"code": "digit"}, {"code": "special"}]``. Each rule is a mapping (a Pydantic model or a dataclass is read as one) of
   ``code`` and, for ``min_length`` only, ``value``; a rule without a value may leave the key out or carry it null, so it
   is read with ``.get("value")``. Its codes are the ones ``failed_rules`` answers, in the same order (POLICY-001 and
   POLICY-002 pin the same list), and its ``min_length`` value is the length the policy applies (POLICY-003).

Every sample character is named as Unicode names it and checked against its category before a case relies on it
(POLICY-000): a case about uppercase letters must hold an ``Lu``, or it proves nothing.

PURE: no database, no server, no environment, nothing written. Red until A6c: the whole module — ``password_policy``
does not exist yet, so the import at the top fails at collection.
"""

import dataclasses
import unicodedata
from typing import Any

import pytest

from backend.app.services.accounts import password_policy
from backend.test_scripts.test_utils import print_section, print_success

#: The codes of the rules, in the policy's order.
RULE_CODES = ["min_length", "uppercase", "lowercase", "digit", "special"]
#: What GET /system/instance publishes, as (code, value): a rule without a value reads None.
PUBLIC_RULES = [("min_length", 8), ("uppercase", None), ("lowercase", None), ("digit", None), ("special", None)]
#: The keys a published rule may carry.
RULE_KEYS = {"code", "value"}

# The sample characters, by the names Unicode gives them; POLICY-000 checks the category each case relies on.
E_ACUTE_CAPITAL = unicodedata.lookup("LATIN CAPITAL LETTER E WITH ACUTE")  # É, Lu
E_ACUTE_SMALL = unicodedata.lookup("LATIN SMALL LETTER E WITH ACUTE")  # é, Ll
U_DIAERESIS_SMALL = unicodedata.lookup("LATIN SMALL LETTER U WITH DIAERESIS")  # ü, Ll
HAN_CHARACTER = unicodedata.lookup("CJK UNIFIED IDEOGRAPH-6F22")  # 漢, Lo: a letter without case
ARABIC_INDIC_THREE = unicodedata.lookup("ARABIC-INDIC DIGIT THREE")  # ٣, Nd
EURO_SIGN = unicodedata.lookup("EURO SIGN")  # €, Sc
LOW_LINE = unicodedata.lookup("LOW LINE")  # _, Pc: a word character for a regular expression, a symbol here
SPACE = unicodedata.lookup("SPACE")  # Zs
NO_BREAK_SPACE = unicodedata.lookup("NO-BREAK SPACE")  # Zs
SUPERSCRIPT_TWO = unicodedata.lookup("SUPERSCRIPT TWO")  # ², No: '²'.isdigit() is True
CIRCLED_CAPITAL_A = unicodedata.lookup("CIRCLED LATIN CAPITAL LETTER A")  # Ⓐ, So: 'Ⓐ'.isupper() is True
FEMININE_ORDINAL = unicodedata.lookup("FEMININE ORDINAL INDICATOR")  # ª, Lo: 'ª'.islower() is True
BOLD_CAPITAL_A = unicodedata.lookup("MATHEMATICAL BOLD CAPITAL A")  # Lu, outside the BMP: two UTF-16 units, four UTF-8 bytes
BOLD_SMALL_A = unicodedata.lookup("MATHEMATICAL BOLD SMALL A")  # Ll, outside the BMP
BOLD_DIGIT_ONE = unicodedata.lookup("MATHEMATICAL BOLD DIGIT ONE")  # Nd, outside the BMP

SAMPLE_CATEGORIES = [
    pytest.param(E_ACUTE_CAPITAL, "Lu", id="E-acute-Lu"),
    pytest.param(E_ACUTE_SMALL, "Ll", id="e-acute-Ll"),
    pytest.param(U_DIAERESIS_SMALL, "Ll", id="u-diaeresis-Ll"),
    pytest.param(HAN_CHARACTER, "Lo", id="han-Lo"),
    pytest.param(ARABIC_INDIC_THREE, "Nd", id="arabic-indic-three-Nd"),
    pytest.param(EURO_SIGN, "Sc", id="euro-sign-Sc"),
    pytest.param(LOW_LINE, "Pc", id="low-line-Pc"),
    pytest.param(SPACE, "Zs", id="space-Zs"),
    pytest.param(NO_BREAK_SPACE, "Zs", id="no-break-space-Zs"),
    pytest.param(SUPERSCRIPT_TWO, "No", id="superscript-two-No"),
    pytest.param(CIRCLED_CAPITAL_A, "So", id="circled-A-So"),
    pytest.param(FEMININE_ORDINAL, "Lo", id="feminine-ordinal-Lo"),
    pytest.param(BOLD_CAPITAL_A, "Lu", id="bold-A-Lu"),
    pytest.param(BOLD_SMALL_A, "Ll", id="bold-a-Ll"),
    pytest.param(BOLD_DIGIT_ONE, "Nd", id="bold-one-Nd"),
]

#: Four characters, one per class (Lu, Ll, Nd, a symbol), nine UTF-8 bytes; twice is eight characters, eighteen bytes.
_UNICODE_QUARTET = f"{E_ACUTE_CAPITAL}{E_ACUTE_SMALL}{ARABIC_INDIC_THREE}{EURO_SIGN}"
#: Four characters, one per class, three of them outside the BMP: seven UTF-16 units, thirteen UTF-8 bytes.
_ASTRAL_QUARTET = f"{BOLD_CAPITAL_A}{BOLD_SMALL_A}{BOLD_DIGIT_ONE}!"

#: (password, the codes it misses): each rule met, or missed alone, with ASCII characters and with Unicode ones.
ONE_RULE_CASES = [
    # min_length: characters — code points, len() of the password as given —, not bytes nor UTF-16 units.
    pytest.param("Abcdef1!", [], id="eight-ascii-characters"),
    pytest.param("Abcde1!", ["min_length"], id="seven-ascii-characters"),
    pytest.param(_UNICODE_QUARTET * 2, [], id="eight-characters-eighteen-utf8-bytes"),
    pytest.param((_UNICODE_QUARTET * 2)[:7], ["min_length"], id="seven-characters-fifteen-utf8-bytes"),
    pytest.param(_ASTRAL_QUARTET * 2, [], id="eight-characters-outside-the-bmp"),
    pytest.param((_ASTRAL_QUARTET * 2)[:7], ["min_length"], id="seven-characters-thirteen-utf16-units"),
    pytest.param(f"{SPACE}Abcde1!", [], id="a-leading-space-counts-toward-the-length"),
    # uppercase: a character of category Lu.
    pytest.param("abcdef1!", ["uppercase"], id="no-uppercase-ascii"),
    pytest.param(f"{E_ACUTE_CAPITAL}bcdef1!", [], id="uppercase-met-by-E-acute"),
    pytest.param(f"{E_ACUTE_SMALL}crire12!", ["uppercase"], id="e-acute-is-not-uppercase"),
    # lowercase: Ll.
    pytest.param("ABCDEF1!", ["lowercase"], id="no-lowercase-ascii"),
    pytest.param(f"ABCDE{E_ACUTE_SMALL}1!", [], id="lowercase-met-by-e-acute"),
    pytest.param(f"{E_ACUTE_CAPITAL}CRIRE12!", ["lowercase"], id="E-acute-is-not-lowercase"),
    # digit: Nd.
    pytest.param("Abcdefg!", ["digit"], id="no-digit-ascii"),
    pytest.param(f"Abcdef{ARABIC_INDIC_THREE}!", [], id="digit-met-by-arabic-indic-three"),
    pytest.param(f"{E_ACUTE_CAPITAL}cri{U_DIAERESIS_SMALL}re!", ["digit"], id="no-digit-unicode-letters"),
    # special: neither a letter, nor a number, nor whitespace.
    pytest.param("Abcdefg1", ["special"], id="no-symbol-ascii"),
    pytest.param(f"Abcdef1{EURO_SIGN}", [], id="symbol-met-by-euro-sign"),
    pytest.param(f"Abcdef1{LOW_LINE}", [], id="symbol-met-by-low-line"),
    pytest.param(f"Ecrire12{SPACE}", ["special"], id="a-space-is-not-a-symbol"),
    pytest.param(f"Ecrire{NO_BREAK_SPACE}12", ["special"], id="a-no-break-space-is-not-a-symbol"),
    pytest.param(f"Ecrire12{U_DIAERESIS_SMALL}", ["special"], id="u-diaeresis-is-a-letter-not-a-symbol"),
]

#: (password, the codes it misses): several rules missed come back in the policy's order, whatever the password's order.
SEVERAL_RULES_CASES = [
    pytest.param("abc", ["min_length", "uppercase", "digit", "special"], id="three-lowercase-letters"),
    pytest.param("!1A", ["min_length", "lowercase"], id="symbol-digit-uppercase"),
    pytest.param("12345678", ["uppercase", "lowercase", "special"], id="eight-digits"),
    pytest.param("!!!!!!!!", ["uppercase", "lowercase", "digit"], id="eight-symbols"),
    pytest.param(SPACE * 8, ["uppercase", "lowercase", "digit", "special"], id="eight-spaces"),
    pytest.param("testpassword123", ["uppercase", "special"], id="the-test-suites-old-password"),
    pytest.param(f"{HAN_CHARACTER * 6}12!", ["uppercase", "lowercase"], id="letters-without-case"),
]

#: (password, the codes it misses): where the category and the str methods of the old command-line copy part ways.
CATEGORY_DECIDES_CASES = [
    pytest.param(f"Ecrire{SUPERSCRIPT_TWO * 2}!", ["digit"], id="superscript-two-is-not-a-digit"),
    pytest.param(f"Ecrire12{SUPERSCRIPT_TWO}", ["special"], id="superscript-two-is-a-number-not-a-symbol"),
    pytest.param(f"ecrire12!{CIRCLED_CAPITAL_A}", ["uppercase"], id="circled-A-is-not-an-uppercase-letter"),
    pytest.param(f"Ecrire12{CIRCLED_CAPITAL_A}", [], id="circled-A-is-a-symbol"),
    pytest.param(f"ECRIRE12!{FEMININE_ORDINAL}", ["lowercase"], id="feminine-ordinal-is-not-a-lowercase-letter"),
    pytest.param(f"Ecrire12{FEMININE_ORDINAL}", ["special"], id="feminine-ordinal-is-a-letter-not-a-symbol"),
]


def _published() -> Any:
    """``password_rules_public``: called when it is a function, read when it is a constant."""
    published = password_policy.password_rules_public
    return published() if callable(published) else published


def _as_mapping(rule: Any) -> Any:
    """A published rule as a plain mapping: a Pydantic model as it serializes to JSON, a dataclass as its fields, anything else as it is."""
    if hasattr(rule, "model_dump"):
        return rule.model_dump(mode="json")
    if dataclasses.is_dataclass(rule) and not isinstance(rule, type):
        return dataclasses.asdict(rule)
    return rule


def _pairs(rules: Any) -> Any:
    """``(code, value)`` of every rule, a value left out reading as a null one; the rules as they are when they are not a sequence of mappings of code and value alone, so that the comparison fails and shows them."""
    if not isinstance(rules, (list, tuple)):
        return rules
    mappings = [_as_mapping(rule) for rule in rules]
    if not all(isinstance(rule, dict) and set(rule) <= RULE_KEYS for rule in mappings):
        return mappings
    return [(rule.get("code"), rule.get("value")) for rule in mappings]


def _describe(password: str) -> str:
    """The password with every character's category: what a failure must show to be read."""
    return f"{password!r} ({' '.join(unicodedata.category(character) for character in password)})"


@pytest.mark.parametrize(("character", "category"), SAMPLE_CATEGORIES)
def test_every_sample_is_of_the_category_its_cases_rely_on(character: str, category: str) -> None:
    """POLICY-000 — the test's own barrier: each sample character is of the Unicode category the cases below rely on."""
    found = unicodedata.category(character)

    assert found == category, f"test bug: {unicodedata.name(character)} ({character!r}) is {found}, not {category}: the cases built on it prove nothing"


def test_the_published_rules_are_the_five_of_today_in_order() -> None:
    """POLICY-001: ``password_rules_public`` is exactly ``[min_length 8, uppercase, lowercase, digit, special]``, each rule a mapping of ``code`` and, for ``min_length`` only, ``value`` (left out or null for the others)."""
    print_section("POLICY-001: the rules GET /system/instance publishes")
    published = _published()

    assert isinstance(published, (list, tuple)), f"password_rules_public must be a list of rules: got {published!r}"
    assert _pairs(published) == PUBLIC_RULES, f"password_rules_public must be {PUBLIC_RULES} as (code, value) — keys code and value only, a value left out reading as null —: got {published!r}"
    print_success(f"published: {PUBLIC_RULES}")


def test_the_empty_password_misses_every_rule_in_the_policys_order() -> None:
    """POLICY-002: ``failed_rules("")`` is a list of the five codes, in the policy's order — the order of the published rules."""
    print_section("POLICY-002: the empty password misses every rule, in order")
    missed = password_policy.failed_rules("")

    assert isinstance(missed, list), f"failed_rules must answer a list of codes: got {missed!r}"
    assert missed == RULE_CODES, f"the empty password misses every rule, in the policy's order {RULE_CODES}: got {missed}"
    print_success(f"failed_rules('') = {missed}")


def test_the_published_length_is_the_length_applied() -> None:
    """POLICY-003: a password exactly as long as the published ``min_length`` value, meeting every other rule, meets them all; one character fewer misses ``min_length`` alone."""
    print_section("POLICY-003: the published min_length is the length applied")
    pairs = _pairs(_published())
    values = [pair[1] for pair in pairs if isinstance(pair, tuple) and pair[0] == "min_length"] if isinstance(pairs, list) else []
    assert len(values) == 1 and isinstance(values[0], int) and values[0] >= 4, f"the published rules must carry min_length once, with an integer value of at least 4: {pairs!r}"
    length = values[0]
    exact = "Aa1!" + "a" * (length - 4)

    assert password_policy.failed_rules(exact) == [], f"{exact!r} is {length} characters long, the published min_length, and meets every other rule: failed_rules says {password_policy.failed_rules(exact)}"
    assert password_policy.failed_rules(exact[:-1]) == ["min_length"], f"{exact[:-1]!r} is one character short of the published min_length {length}: failed_rules says {password_policy.failed_rules(exact[:-1])}"
    print_success(f"{length} characters pass, {length - 1} miss min_length")


@pytest.mark.parametrize(("password", "missed"), ONE_RULE_CASES)
def test_each_rule_is_met_or_missed_by_its_class_of_characters(password: str, missed: list[str]) -> None:
    """POLICY-004: each rule met, or missed alone, with ASCII and with Unicode characters: É uppercase and é lowercase, ٣ a digit, € and _ symbols, a space (a no-break one too) no symbol, ü a letter; the length counted in characters."""
    found = password_policy.failed_rules(password)

    assert found == missed, f"failed_rules({_describe(password)}), {len(password)} characters: expected {missed}, got {found}"


@pytest.mark.parametrize(("password", "missed"), SEVERAL_RULES_CASES)
def test_several_rules_missed_come_back_in_the_policys_order(password: str, missed: list[str]) -> None:
    """POLICY-005: several rules missed are answered in the policy's order (min_length, uppercase, lowercase, digit, special), whatever order the password shows its characters in; a letter without case (漢) meets neither uppercase nor lowercase, and is no symbol."""
    found = password_policy.failed_rules(password)

    assert found == missed, f"failed_rules({_describe(password)}): expected {missed}, in the policy's order, got {found}"


@pytest.mark.parametrize(("password", "missed"), CATEGORY_DECIDES_CASES)
def test_the_unicode_category_decides_where_the_str_methods_disagree(password: str, missed: list[str]) -> None:
    """POLICY-006 — the part of the night decision under review: where Unicode's categories and Python's ``str`` methods, which the old command-line copy used, part ways, the category decides.

    ``'²'.isdigit()`` is True, but ² is ``No``: a number, so neither a digit nor a symbol. ``'Ⓐ'.isupper()`` is True, but Ⓐ
    is ``So``: a symbol, not an uppercase letter. ``'ª'.islower()`` is True, but ª is ``Lo``: a letter, so not a symbol,
    and not a lowercase one. If the review changes the classes, these cases change with it.
    """
    found = password_policy.failed_rules(password)

    assert found == missed, f"failed_rules({_describe(password)}): the category decides, expected {missed}, got {found}"


# =============================================================================
# B4 (workstream B): rule lists
# =============================================================================
#
# Release 1.3, workstream B, lot B4, the «secure» backup (decision P12): the password of an archive follows these rules
# with at least 12 characters, and never a copy of them. B writes three changes in this module and A reviews them
# (``b4-test-brief.md`` §2):
#
# - ``failed_rules(password, rules=None)`` and ``password_rules_public(rules=None)`` apply, or publish, the rules they
#   are given. ``None`` is this module's ``PASSWORD_RULES`` READ AT CALL TIME, never a default bound at import, so a
#   change of A's rules reaches every caller. Without ``rules=`` both answer exactly as before: POLICY-000 to POLICY-006
#   above are unchanged, and B4-RULES-09 compares the forms.
# - ``rules_with_minimum_length(minimum, rules=None)``: a tuple of the rules with ``min_length`` at ``max(its value,
#   minimum)``, never lowered, the rules' order kept and the other rules as they are; a list without ``min_length``
#   gains it first; ``ValueError`` for a minimum below 1.
#
# Red until B4: ``rules_with_minimum_length`` does not exist and neither function takes ``rules=``. Each new name is
# read through the module inside the tests, never imported at the top, so the tests above still collect and pass.

#: The archive's minimum (P12), and a minimum A might one day raise its own to, above the archive's.
B4_ARCHIVE_MINIMUM = 12
B4_RAISED_POLICY_MINIMUM = 14
#: The rules of an archive as (code, value): A's five in A's order, ``min_length`` at 12.
B4_ARCHIVE_RULES = [(code, B4_ARCHIVE_MINIMUM if code == "min_length" else None) for code in RULE_CODES]


def _b4_rule(code: str, value: int | None = None) -> Any:
    """A rule of the policy's own type, for the lists a test gives."""
    return password_policy.PasswordRule(code, value)


def _b4_rule_pairs(rules: Any) -> Any:
    """``(code, value)`` of each rule; anything but a sequence of ``PasswordRule`` as it is, so that the comparison fails and shows it."""
    if not isinstance(rules, (list, tuple)) or not all(isinstance(rule, password_policy.PasswordRule) for rule in rules):
        return rules
    return [(rule.code, rule.value) for rule in rules]


def _b4_meeting_every_class(length: int) -> str:
    """``length`` characters, at least four, meeting every class: ``Aa1!``, then lowercase letters."""
    return "Aa1!" + "a" * (length - 4)


#: (password, the codes it misses) against the archive's rules, ``rules_with_minimum_length(12)``.
B4_ARCHIVE_CASES = [
    pytest.param(_b4_meeting_every_class(11), ["min_length"], id="eleven-characters-meeting-every-class"),
    pytest.param(_b4_meeting_every_class(12), [], id="twelve-characters-meeting-every-class"),
    pytest.param("Aa!" + "a" * 9, ["digit"], id="twelve-characters-without-a-digit"),
    pytest.param("Abcdef1!", ["min_length"], id="eight-characters-enough-for-the-policy-alone"),
    pytest.param("abc", ["min_length", "uppercase", "digit", "special"], id="several-missed-in-the-rules-order"),
    pytest.param(_UNICODE_QUARTET * 3, [], id="twelve-characters-twenty-seven-utf8-bytes"),
    pytest.param((_UNICODE_QUARTET * 3)[:11], ["min_length"], id="eleven-characters-twenty-four-utf8-bytes"),
]

#: (the rules given, as (code, value); what ``rules_with_minimum_length(12, rules=…)`` answers, as (code, value)).
B4_GIVEN_LISTS = [
    pytest.param([("digit", None), ("special", None)], [("min_length", 12), ("digit", None), ("special", None)], id="without-min-length-gains-it-first"),
    pytest.param([], [("min_length", 12)], id="an-empty-list-is-not-none-and-gains-min-length-alone"),
    pytest.param([("digit", None), ("min_length", 10), ("special", None)], [("digit", None), ("min_length", 12), ("special", None)], id="min-length-raised-where-it-stands"),
    pytest.param([("min_length", 16), ("uppercase", None)], [("min_length", 16), ("uppercase", None)], id="a-higher-minimum-kept"),
]

#: Every password of the cases above, and the empty one: what the forms of ``failed_rules`` must answer alike.
B4_SAMPLE_PASSWORDS = ["", *(case.values[0] for case in (*ONE_RULE_CASES, *SEVERAL_RULES_CASES, *CATEGORY_DECIDES_CASES))]


def test_b4_rules_with_minimum_length_raises_min_length_and_keeps_the_rest() -> None:
    """B4-RULES-01: ``rules_with_minimum_length(12)`` is a tuple of ``PasswordRule``: A's codes in A's order, ``min_length`` at 12, every other rule exactly as A has it; A's own ``PASSWORD_RULES`` are left as they were, ``min_length`` 8."""
    print_section("B4-RULES-01: A's rules with a minimum of 12")
    policy = password_policy.PASSWORD_RULES

    rules = password_policy.rules_with_minimum_length(B4_ARCHIVE_MINIMUM)

    assert isinstance(rules, tuple) and all(isinstance(rule, password_policy.PasswordRule) for rule in rules), f"rules_with_minimum_length must answer a tuple of PasswordRule: got {rules!r}"
    assert [rule.code for rule in rules] == [rule.code for rule in policy], f"the codes of PASSWORD_RULES in their order, {[rule.code for rule in policy]}: got {[rule.code for rule in rules]}"
    assert _b4_rule_pairs(rules) == B4_ARCHIVE_RULES, f"min_length at {B4_ARCHIVE_MINIMUM}, the other rules without a value: expected {B4_ARCHIVE_RULES}, got {_b4_rule_pairs(rules)}"
    others = [rule for rule in rules if rule.code != "min_length"]
    assert others == [rule for rule in policy if rule.code != "min_length"], f"every rule but min_length exactly as A has it: got {others!r}"
    assert password_policy.PASSWORD_RULES is policy and _b4_rule_pairs(policy) == PUBLIC_RULES, f"A's own rules are never changed: PASSWORD_RULES is now {password_policy.PASSWORD_RULES!r}"
    print_success(f"rules_with_minimum_length(12) = {_b4_rule_pairs(rules)}")


@pytest.mark.parametrize("minimum", [pytest.param(1, id="1"), pytest.param(4, id="4"), pytest.param(8, id="8-the-policys-own")])
def test_b4_rules_with_minimum_length_never_lowers_the_minimum(minimum: int) -> None:
    """B4-RULES-02: a minimum at or below A's 8 changes nothing: ``rules_with_minimum_length(4)`` keeps A's 8, the rules as A has them."""
    rules = password_policy.rules_with_minimum_length(minimum)

    assert _b4_rule_pairs(rules) == PUBLIC_RULES, f"rules_with_minimum_length({minimum}) never lowers A's minimum: expected A's rules {PUBLIC_RULES}, got {_b4_rule_pairs(rules)}"


@pytest.mark.parametrize(("given", "expected"), B4_GIVEN_LISTS)
def test_b4_rules_with_minimum_length_on_the_rules_it_is_given(given: list[tuple[str, int | None]], expected: list[tuple[str, int | None]]) -> None:
    """B4-RULES-03: on the rules it is given (``rules=``, an empty list included, which is not ``None``): a list without ``min_length`` gains it first, ``min_length`` is raised where it stands, a higher minimum is kept, the other rules keep their order; the list given is never changed."""
    rules = [_b4_rule(code, value) for code, value in given]
    untouched = list(rules)

    result = password_policy.rules_with_minimum_length(B4_ARCHIVE_MINIMUM, rules=rules)

    assert _b4_rule_pairs(result) == expected, f"rules_with_minimum_length(12, rules={given}): expected {expected}, got {result!r}"
    assert rules == untouched, f"the list given must never be changed: it is now {rules!r}"


@pytest.mark.parametrize("minimum", [pytest.param(0, id="0"), pytest.param(-1, id="-1")])
def test_b4_rules_with_minimum_length_refuses_a_minimum_below_1(minimum: int) -> None:
    """B4-RULES-04: a minimum below 1 is a ``ValueError``."""
    rules_with_minimum_length = password_policy.rules_with_minimum_length

    with pytest.raises(ValueError):
        rules_with_minimum_length(minimum)


def test_b4_without_rules_the_policys_rules_are_read_at_call_time(monkeypatch: pytest.MonkeyPatch) -> None:
    """B4-RULES-05: no ``rules`` (or ``rules=None``) is ``PASSWORD_RULES`` as it is at the call, never a default bound at import. With A's minimum raised to 14 (``PASSWORD_RULES`` replaced): ``rules_with_minimum_length(12)`` gives 14; ``failed_rules`` reports ``min_length`` for 13 characters meeting every class and nothing for 14; ``password_rules_public`` publishes 14."""
    print_section("B4-RULES-05: A's rules read at call time")
    raised = tuple(dataclasses.replace(rule, value=B4_RAISED_POLICY_MINIMUM) if rule.code == "min_length" else rule for rule in password_policy.PASSWORD_RULES)
    monkeypatch.setattr(password_policy, "PASSWORD_RULES", raised)
    expected = [(code, B4_RAISED_POLICY_MINIMUM if code == "min_length" else None) for code in RULE_CODES]
    thirteen, fourteen = _b4_meeting_every_class(13), _b4_meeting_every_class(14)

    archive = password_policy.rules_with_minimum_length(B4_ARCHIVE_MINIMUM)

    assert _b4_rule_pairs(archive) == expected, f"A's minimum raised to 14: rules_with_minimum_length(12) must give 14, expected {expected}, got {_b4_rule_pairs(archive)}"
    for given in ({}, {"rules": None}):
        form = "rules=None" if given else "without rules="
        assert password_policy.failed_rules(thirteen, **given) == ["min_length"], f"failed_rules({thirteen!r}), {form}: 13 characters, A's minimum is now 14: got {password_policy.failed_rules(thirteen, **given)}"
        assert password_policy.failed_rules(fourteen, **given) == [], f"failed_rules({fourteen!r}), {form}: 14 characters meeting every class: got {password_policy.failed_rules(fourteen, **given)}"
        assert _pairs(password_policy.password_rules_public(**given)) == expected, f"password_rules_public, {form}: A's rules as they are now, {expected}: got {password_policy.password_rules_public(**given)!r}"
    print_success("rules_with_minimum_length(12), failed_rules and password_rules_public follow A's 14")


@pytest.mark.parametrize(("password", "missed"), B4_ARCHIVE_CASES)
def test_b4_failed_rules_applies_the_rules_it_is_given(password: str, missed: list[str]) -> None:
    """B4-RULES-06: ``failed_rules(password, rules=rules_with_minimum_length(12))``: 11 characters meeting every class miss ``min_length`` alone, 12 meet them all, 12 without a digit miss ``digit`` alone; 8, enough for A's rules, miss ``min_length``; several codes come back in the rules' order; the length counts characters, Unicode ones included."""
    found = password_policy.failed_rules(password, rules=password_policy.rules_with_minimum_length(B4_ARCHIVE_MINIMUM))

    assert found == missed, f"failed_rules({_describe(password)}, rules=rules_with_minimum_length(12)), {len(password)} characters: expected {missed}, got {found}"


def test_b4_failed_rules_answers_in_the_order_of_the_rules_it_is_given() -> None:
    """B4-RULES-07: the codes come back in the order of the rules given, not A's, and only the rules given apply: ``"ABC"`` against special, digit, min_length 12 and uppercase misses the first three, and no ``lowercase``, a rule it was not given."""
    rules = (_b4_rule("special"), _b4_rule("digit"), _b4_rule("min_length", B4_ARCHIVE_MINIMUM), _b4_rule("uppercase"))

    found = password_policy.failed_rules("ABC", rules=rules)

    assert found == ["special", "digit", "min_length"], f"failed_rules('ABC', rules={_b4_rule_pairs(rules)}): expected ['special', 'digit', 'min_length'], in the order given and without lowercase, a rule not given: got {found}"


def test_b4_password_rules_public_publishes_the_rules_it_is_given() -> None:
    """B4-RULES-08: ``password_rules_public(rules=…)`` publishes the rules given, in their order, as ``code`` and ``value``: 12 for the archive's ``min_length``, null (or left out, as POLICY-001 allows) for a rule without a value."""
    archive = password_policy.password_rules_public(rules=password_policy.rules_with_minimum_length(B4_ARCHIVE_MINIMUM))
    given = password_policy.password_rules_public(rules=(_b4_rule("digit"), _b4_rule("min_length", 20)))

    assert isinstance(archive, list) and _pairs(archive) == B4_ARCHIVE_RULES, f"the archive's rules as published: expected {B4_ARCHIVE_RULES} as (code, value), keys code and value only, got {archive!r}"
    assert _pairs(given) == [("digit", None), ("min_length", 20)], f"the rules given, in their order: expected [('digit', None), ('min_length', 20)], got {given!r}"


def test_b4_without_rules_both_functions_answer_as_with_the_policys_rules() -> None:
    """B4-RULES-09: without ``rules=``, both functions answer exactly as with ``rules=PASSWORD_RULES`` and with ``rules=None``: ``failed_rules`` on every password of the cases above and on the empty one, ``password_rules_public`` as a whole."""
    print_section("B4-RULES-09: without rules=, A's rules")
    policy = password_policy.PASSWORD_RULES
    differ = []

    for password in B4_SAMPLE_PASSWORDS:
        without, explicit, none = password_policy.failed_rules(password), password_policy.failed_rules(password, rules=policy), password_policy.failed_rules(password, rules=None)
        if not without == explicit == none:
            differ.append(f"{_describe(password)}: without rules= {without}, rules=PASSWORD_RULES {explicit}, rules=None {none}")
    published = (password_policy.password_rules_public(), password_policy.password_rules_public(rules=policy), password_policy.password_rules_public(rules=None))

    assert differ == [], "failed_rules answers differently with and without rules=:\n- " + "\n- ".join(differ)
    assert published[0] == published[1] == published[2], f"password_rules_public: without rules= {published[0]}, rules=PASSWORD_RULES {published[1]}, rules=None {published[2]}"
    print_success(f"{len(B4_SAMPLE_PASSWORDS)} passwords and the published rules, alike in the three forms")
