"""
The enricher contract (plan 68, lot B1): what ``EnricherRegistry`` refuses at registration, what every enricher it
discovers declares, and what the test enricher ``mockenrich`` answers.

Under test: ``backend/app/services/enrichers/base.py`` (the contract, its docstrings), ``enrichers/registry.py``
(``EnricherRegistry``, ``EnricherDeclarationError``) and ``enricher_providers/mockenrich/plugin.py`` (the test double).

1. **The declarations** a class must carry, checked by the registry at registration: a class that breaks one is refused
   with ``EnricherDeclarationError`` and never stored.

   - ``code``: a non-empty lowercase identifier, ``[a-z][a-z0-9_]*``; ``name``: non-empty text; ``terms``: an
     ``EnricherTerms`` member, never its bare text;
   - ``accepted_identifier_types``: a non-empty tuple of upper-case strings;
   - ``default_priority``: exactly every ``AssetType`` member as key (one missing, or one extra key, refused), each value
     an ``int`` of at least 0, or ``None`` for a type the enricher does not cover;
   - ``voices``: per ``AssetType``, a frozenset of catalogue keys (``assets/profile/catalogue.py``, ``CATALOGUE``); an
     unknown key is refused, and so are voices for a type whose degree is ``None``.

   Each refusal is a class built from one valid baseline with exactly one defect, under a code of its own, registered
   with ``EnricherRegistry.register``; then its absence from ``list_plugin_codes()`` and from the storage is checked. The
   baseline itself registers (the control: a registry refusing everything would make every refusal green), and the
   test's own reading of the contract (``contract_problems``) finds the defect in each bad class and nothing in the
   baseline, so a case cannot be bad by accident.

2. **Every discovered enricher keeps the contract**, in test mode, so ``mockenrich`` is among them: the list is not
   empty, nothing failed to load, and ``contract_problems`` finds nothing.

3. **``mockenrich``** answers what its module docstring promises, with its own constants (read from the module the
   registry loaded the class from): ``recognize`` finds any identifier but those starting with ``UNKNOWN_PREFIX``, names
   it ``Mock <identifier>``, and an ISIN brings the LEI ``lei_of(isin)``; ``read`` yields one item per binding, in order,
   ``OK`` with ``READ_VALUES`` plus a description and ``SOURCE_DATE``, ``NOT_FOUND``, ``ERROR``, and ``ERROR`` with
   ``RATE_LIMITED`` and ``RATE_LIMITED_RETRY_AFTER``; ``page_url`` is an address; it does not search; it is ``test_only``,
   so outside test mode the registry neither lists it nor finds it.

Red reason before the registry's checks are written: ``EnricherRegistry._validate_plugin_class`` raises
``NotImplementedError``. Every registration in section 1 fails with it, and the discovery of ``mockenrich`` fails the
same way, so the registry holds no enricher: sections 2 and 3 fail on their presence barriers. The module itself
imports only what loads today; the plugin module is imported in the tests' bodies, never at collection.

Test mode is driven through ``monkeypatch`` (``LIBREFOLIO_TEST_MODE``), with a barrier that ``is_test_mode()`` reads it,
as ``test_test_only_providers.py`` does.

PURE: no database, no server, no network. The synthetic classes are registered in the real ``EnricherRegistry`` and
removed at each test's teardown, with their environment claims.
"""

from __future__ import annotations

import importlib
import re
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from types import ModuleType

import pytest

from backend.app.config import is_test_mode
from backend.app.db.models import AssetType
from backend.app.services.assets.profile.catalogue import CATALOGUE
from backend.app.services.enrichers.base import (
    RATE_LIMITED,
    EnricherBinding,
    EnricherPlugin,
    EnricherRateLimited,
    EnricherReadItem,
    EnricherReadStatus,
    EnricherRecognition,
    EnricherTerms,
)
from backend.app.services.enrichers.registry import EnricherDeclarationError, EnricherRegistry
from backend.app.services.plugin_settings.fields import release_env_variables
from backend.app.utils.runtime.cooldown import RateLimitedError
from backend.test_scripts.test_utils import print_section, print_success

TEST_MODE_VARIABLE = "LIBREFOLIO_TEST_MODE"
MOCK_CODE = "mockenrich"
CODE_PATTERN = re.compile(r"[a-z][a-z0-9_]*")
#: The settings family the enricher registry names: the claims of a synthetic class are released under it.
SETTINGS_FAMILY = "enricher"
#: Where every synthetic code starts: no real enricher is called this.
LAB_PREFIX = "lab_enricher_"


# =============================================================================
# Test mode
# =============================================================================


def _test_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test mode for the whole test, as the runner runs every pytest process; the barrier proves ``is_test_mode()`` reads it."""
    monkeypatch.setenv(TEST_MODE_VARIABLE, "1")
    assert is_test_mode() is True, f"barrier: with {TEST_MODE_VARIABLE}=1 is_test_mode() is false"


@contextmanager
def _production(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """A production instance for the length of the block, put back on leaving it."""
    with monkeypatch.context() as patch:
        patch.setenv(TEST_MODE_VARIABLE, "0")
        assert is_test_mode() is False, f"barrier: with {TEST_MODE_VARIABLE}=0 is_test_mode() is still true"
        yield


# =============================================================================
# The contract, as this file reads it
# =============================================================================


def contract_problems(plugin_class: type) -> list[str]:  # noqa: C901 — one flat list of rules, as the contract reads
    """What breaks the declarations of ``enrichers/base.py`` in ``plugin_class``: one line per breach, none when it keeps them."""
    problems: list[str] = []
    code = getattr(plugin_class, "code", None)
    if not isinstance(code, str) or not CODE_PATTERN.fullmatch(code):
        problems.append(f"code {code!r}: not a lowercase identifier [a-z][a-z0-9_]*")
    name = getattr(plugin_class, "name", None)
    if not isinstance(name, str) or not name.strip():
        problems.append(f"name {name!r}: empty or not text")
    terms = getattr(plugin_class, "terms", None)
    if not isinstance(terms, EnricherTerms):
        problems.append(f"terms {terms!r}: not an EnricherTerms")
    types = getattr(plugin_class, "accepted_identifier_types", None)
    if not isinstance(types, tuple) or not types or not all(isinstance(kind, str) and kind and kind == kind.upper() for kind in types):
        problems.append(f"accepted_identifier_types {types!r}: not a non-empty tuple of upper-case strings")

    priority = getattr(plugin_class, "default_priority", None)
    if not isinstance(priority, Mapping):
        problems.append(f"default_priority {priority!r}: not a mapping")
        priority = {}
    else:
        members = set(AssetType)
        missing = [asset_type.value for asset_type in AssetType if asset_type not in priority]
        extra = [key for key in priority if key not in members]
        if missing:
            problems.append(f"default_priority: no degree for {missing}")
        if extra:
            problems.append(f"default_priority: keys that are no AssetType {extra!r}")
        wrong = {key: value for key, value in priority.items() if not (value is None or (isinstance(value, int) and not isinstance(value, bool) and value >= 0))}
        if wrong:
            problems.append(f"default_priority: degrees that are neither an int >= 0 nor None {wrong!r}")

    voices = getattr(plugin_class, "voices", None)
    if not isinstance(voices, Mapping):
        problems.append(f"voices {voices!r}: not a mapping")
    else:
        for asset_type, keys in voices.items():
            if asset_type not in set(AssetType):
                problems.append(f"voices: {asset_type!r} is no AssetType")
                continue
            if not isinstance(keys, frozenset):
                problems.append(f"voices[{asset_type}]: {keys!r} is not a frozenset")
                continue
            unknown = sorted(keys - set(CATALOGUE))
            if unknown:
                problems.append(f"voices[{asset_type}]: {unknown} are not catalogue keys")
            if keys and priority.get(asset_type) is None:
                problems.append(f"voices[{asset_type}]: voices for a type it does not cover (degree None)")
    return problems


# =============================================================================
# The synthetic enrichers
# =============================================================================

_ABSENT = object()


def _baseline(code: str) -> dict[str, object]:
    """A valid set of declarations: every degree, one type not covered, voices only for covered types."""
    return {
        "code": code,
        "name": "Lab enricher (testing)",
        "terms": EnricherTerms.OPEN,
        "accepted_identifier_types": ("ISIN", "LEI"),
        "default_priority": {asset_type: None if asset_type == AssetType.INDEX else 10 for asset_type in AssetType},
        "voices": {AssetType.ETF: frozenset({"ter", "geography"}), AssetType.STOCK: frozenset({"sector"})},
    }


class _LabMethods(EnricherPlugin):
    """The abstract methods, implemented once: a synthetic class differs from another by its declarations only."""

    def recognize(self, binding: EnricherBinding) -> EnricherRecognition:
        return EnricherRecognition(found=False)

    def read(self, bindings, keys=None) -> Iterator[EnricherReadItem]:
        yield from ()

    def page_url(self, binding: EnricherBinding) -> str | None:
        return None

    @property
    def test_cases(self) -> list[dict]:
        return []


def _enricher(case: str, **changes: object) -> type:
    """A synthetic enricher: the baseline under the code ``lab_enricher_<case>``, with ``changes`` applied (``_ABSENT``
    drops a declaration). A ``code`` change replaces the code too."""
    attributes = _baseline(f"{LAB_PREFIX}{case}")
    for key, value in changes.items():
        if value is _ABSENT:
            attributes.pop(key, None)
        else:
            attributes[key] = value
    return type(f"LabEnricher_{case}", (_LabMethods,), attributes)


def _priority(**changes: object) -> dict[object, object]:
    """The baseline's degrees with ``changes`` (an AssetType name → its degree; ``_ABSENT`` drops the type)."""
    priority: dict[object, object] = dict(_baseline("unused")["default_priority"])  # type: ignore[arg-type]
    for member, value in changes.items():
        if value is _ABSENT:
            priority.pop(AssetType[member])
        else:
            priority[AssetType[member]] = value
    return priority


def _stored(plugin_class: type) -> bool:
    return any(stored is plugin_class for stored in EnricherRegistry._get_storage().values())


@pytest.fixture
def lab_codes() -> Iterator[list[str]]:
    """The codes a test registers or tries to: removed from the registry's storage, with their claims, at teardown."""
    codes: list[str] = []
    yield codes
    storage = EnricherRegistry._get_storage()
    for code in codes:
        stored = storage.get(code)
        if stored is not None and getattr(stored, "__name__", "").startswith("LabEnricher_"):
            storage.pop(code, None)
        release_env_variables(SETTINGS_FAMILY, code)


# The bad classes: (id, the class, the words the test's own check must report).
_REFUSED = (
    ("a-degree-missing", lambda: _enricher("degree_missing", default_priority=_priority(BOND=_ABSENT)), "no degree for ['BOND']"),
    ("an-extra-key", lambda: _enricher("extra_key", default_priority={**_priority(), "NOT_AN_ASSET_TYPE": 1}), "keys that are no AssetType"),
    ("a-negative-degree", lambda: _enricher("negative_degree", default_priority=_priority(BOND=-1)), "neither an int >= 0 nor None"),
    ("a-float-degree", lambda: _enricher("float_degree", default_priority=_priority(BOND=1.5)), "neither an int >= 0 nor None"),
    ("a-text-degree", lambda: _enricher("text_degree", default_priority=_priority(BOND="10")), "neither an int >= 0 nor None"),
    ("an-unknown-voice", lambda: _enricher("unknown_voice", voices={AssetType.ETF: frozenset({"ter", "not_a_catalogue_voice"})}), "are not catalogue keys"),
    ("a-voice-for-an-uncovered-type", lambda: _enricher("uncovered_voice", voices={AssetType.ETF: frozenset({"ter"}), AssetType.INDEX: frozenset({"description"})}), "voices for a type it does not cover"),
    ("no-terms", lambda: _enricher("no_terms", terms=_ABSENT), "not an EnricherTerms"),
    ("terms-as-bare-text", lambda: _enricher("text_terms", terms="open"), "not an EnricherTerms"),
    ("empty-identifier-types", lambda: _enricher("no_identifier_types", accepted_identifier_types=()), "not a non-empty tuple of upper-case strings"),
    ("lowercase-identifier-type", lambda: _enricher("lower_identifier_type", accepted_identifier_types=("isin",)), "not a non-empty tuple of upper-case strings"),
    ("identifier-types-as-a-list", lambda: _enricher("list_identifier_types", accepted_identifier_types=["ISIN"]), "not a non-empty tuple of upper-case strings"),
    ("an-empty-code", lambda: _enricher("empty_code", code=""), "not a lowercase identifier"),
    ("an-upper-case-code", lambda: _enricher("upper_code", code="Lab_Enricher_Upper"), "not a lowercase identifier"),
    ("a-code-starting-with-a-digit", lambda: _enricher("digit_code", code="1lab_enricher"), "not a lowercase identifier"),
    ("a-code-with-a-dash", lambda: _enricher("dash_code", code="lab-enricher-dash"), "not a lowercase identifier"),
    ("no-code", lambda: _enricher("no_code", code=_ABSENT), "not a lowercase identifier"),
    ("an-empty-name", lambda: _enricher("empty_name", name=""), "empty or not text"),
)


# =============================================================================
# 1. The declarations, refused at registration
# =============================================================================


def test_the_contract_check_of_this_file_finds_nothing_in_the_baseline_and_each_defect_in_its_case():
    """The control of the reading itself: the baseline keeps the contract, and each bad class breaks it where its case
    says, so a refusal below is about that defect and nothing else."""
    print_section("Enricher contract: the reading of this file")
    assert "ter" in CATALOGUE and "geography" in CATALOGUE and "sector" in CATALOGUE, "barrier: the baseline's voices are catalogue keys"
    assert contract_problems(_enricher("baseline_reading")) == []
    for case, build, expected in _REFUSED:
        problems = contract_problems(build())
        assert len(problems) == 1 and expected in problems[0], f"{case}: the reading finds {problems}, expected one breach naming {expected!r}"
    print_success(f"the baseline keeps the contract; {len(_REFUSED)} classes each break it once")


def test_the_registry_accepts_a_class_that_keeps_the_contract(lab_codes):
    """The control of every refusal below: the baseline registers, and the registry lists and serves it."""
    print_section("Enricher contract: the baseline registers")
    plugin_class = _enricher("accepted")
    lab_codes.append(plugin_class.code)

    EnricherRegistry.register(plugin_class)

    assert plugin_class.code in EnricherRegistry.list_plugin_codes()
    assert EnricherRegistry.get_plugin(plugin_class.code) is plugin_class
    print_success(f"{plugin_class.code} registered and served")


def test_a_degree_for_none_is_a_type_not_covered(lab_codes):
    """``covers`` reads the degree: ``None`` is a type the enricher does not cover, an int one it does."""
    plugin_class = _enricher("covers")
    lab_codes.append(plugin_class.code)
    EnricherRegistry.register(plugin_class)
    instance = EnricherRegistry.get_plugin_instance(plugin_class.code)
    assert instance is not None, f"barrier: {plugin_class.code} is not served after its registration"

    assert (instance.covers(AssetType.ETF), instance.covers(AssetType.INDEX)) == (True, False)


@pytest.mark.parametrize(("build", "expected"), [pytest.param(build, expected, id=case) for case, build, expected in _REFUSED])
def test_the_registry_refuses_a_class_that_breaks_the_contract(build, expected, lab_codes):
    """Each case breaks the baseline once: ``EnricherDeclarationError``, and the class is not stored."""
    plugin_class = build()
    code = getattr(plugin_class, "code", None)
    lab_codes.append(code if isinstance(code, str) else "")
    assert len(contract_problems(plugin_class)) == 1, "barrier: the class breaks the contract exactly once"
    print_section(f"Enricher contract: refused, {expected}")

    with pytest.raises(EnricherDeclarationError):
        EnricherRegistry.register(plugin_class)

    assert not _stored(plugin_class), f"{plugin_class.__name__} was refused but is stored"
    if isinstance(code, str):
        assert code not in EnricherRegistry.list_plugin_codes(), f"{code!r} was refused but is listed"
    print_success(f"{plugin_class.__name__}: refused and not stored")


def test_the_declaration_error_is_a_value_error():
    """A refusal is a ``ValueError``, as the other declaration errors of the registries are."""
    assert issubclass(EnricherDeclarationError, ValueError)


# =============================================================================
# 2. Every discovered enricher keeps the contract
# =============================================================================


def test_every_discovered_enricher_keeps_the_contract(monkeypatch):
    print_section("Enricher contract: every discovered enricher")
    _test_mode(monkeypatch)
    errors = EnricherRegistry.get_discovery_errors()
    assert errors == (), f"enricher plugins failed to load: {[(failure.module_name, failure.error_type, failure.message) for failure in errors]}"
    codes = [code for code in EnricherRegistry.list_plugin_codes() if not code.startswith(LAB_PREFIX)]
    assert codes, "the registry discovers no enricher: the contract would hold on nothing"
    assert MOCK_CODE in codes, f"barrier: in test mode the test enricher is discovered, found {codes}"

    problems = {code: contract_problems(EnricherRegistry.get_plugin(code)) for code in codes}

    assert {code: found for code, found in problems.items() if found} == {}
    print_success(f"{len(codes)} enrichers keep the contract: {codes}")


def test_a_real_enricher_reaches_an_external_service_and_a_test_double_does_not(monkeypatch):
    """``calls_external_service`` (project 76, K1): every call of an enricher that reaches a source is counted at the
    enrichers' boundary, and refused when an instance limit is full. The base declares it True, as the asset and FX
    bases do; a test-only enricher computes its answers itself and declares False. A real enricher is one the registry
    discovers that is not ``test_only``."""
    print_section("Enricher contract: calls_external_service")
    _test_mode(monkeypatch)
    assert getattr(EnricherPlugin, "calls_external_service", None) is True, "the base declares calls_external_service = True"
    codes = [code for code in EnricherRegistry.list_plugin_codes() if not code.startswith(LAB_PREFIX)]
    declared = {code: getattr(EnricherRegistry.get_plugin(code), "calls_external_service", None) for code in codes}
    test_only = {code for code in codes if EnricherRegistry.get_plugin(code).test_only}
    assert MOCK_CODE in test_only, f"barrier: the test enricher is discovered, found {codes}"
    assert {"justetf", "borsa_italiana", "yfinance"} <= set(codes) - test_only, f"barrier: the three real enrichers are discovered, found {codes}"
    assert {code: declared[code] for code in test_only} == dict.fromkeys(test_only, False), f"a test double reaches no service: {declared}"
    real = set(codes) - test_only
    assert {code: declared[code] for code in real} == dict.fromkeys(real, True), f"a real enricher reaches its source: {declared}"
    print_success(f"real {sorted(real)} counted, test doubles {sorted(test_only)} not")


# =============================================================================
# 3. The test enricher
# =============================================================================


def _mock(monkeypatch: pytest.MonkeyPatch) -> tuple[EnricherPlugin, ModuleType]:
    """The test enricher as the registry serves it in test mode, and the module its class was loaded from (its constants).

    Called in a test's body: the plugin module is never imported at collection."""
    _test_mode(monkeypatch)
    plugin_class = EnricherRegistry.get_plugin(MOCK_CODE)
    assert plugin_class is not None, f"barrier: in test mode the registry serves no {MOCK_CODE!r} (discovery errors: {EnricherRegistry.get_discovery_errors()})"
    instance = EnricherRegistry.get_plugin_instance(MOCK_CODE)
    assert isinstance(instance, plugin_class), f"barrier: {MOCK_CODE} is listed but cannot be instantiated"
    return instance, importlib.import_module(plugin_class.__module__)


def test_mockenrich_recognizes_any_identifier_and_brings_the_lei_of_an_isin(monkeypatch):
    print_section("mockenrich: recognize")
    mock, module = _mock(monkeypatch)
    isin = EnricherBinding("ISIN", "IE00B4L5Y983")
    ticker = EnricherBinding("TICKER", "SWDA")

    found = mock.recognize(isin)
    other = mock.recognize(ticker)

    assert (found.found, found.name, found.page_url) == (True, "Mock IE00B4L5Y983", mock.page_url(isin))
    assert dict(found.identifiers) == {"LEI": module.lei_of(isin.identifier)}
    assert len(module.lei_of(isin.identifier)) == 20
    assert (other.found, other.name, dict(other.identifiers)) == (True, "Mock SWDA", {}), "only an ISIN brings the LEI"
    print_success("found, named, and the LEI of an ISIN")


def test_mockenrich_does_not_find_an_identifier_with_the_unknown_prefix(monkeypatch):
    mock, module = _mock(monkeypatch)
    unknown = EnricherBinding("ISIN", f"{module.UNKNOWN_PREFIX}0000001")

    recognition = mock.recognize(unknown)

    assert recognition.found is False
    assert (recognition.name, dict(recognition.identifiers)) == (None, {})


def test_mockenrich_reads_one_item_per_binding_in_order_with_its_outcome(monkeypatch):
    print_section("mockenrich: read")
    mock, module = _mock(monkeypatch)
    bindings = [
        EnricherBinding("ISIN", "IE00B4L5Y983"),
        EnricherBinding("ISIN", module.NOT_FOUND_IDENTIFIER),
        EnricherBinding("ISIN", module.ERROR_IDENTIFIER),
        EnricherBinding("ISIN", module.RATE_LIMITED_IDENTIFIER),
        EnricherBinding("LEI", "LAB0000000000000000X"),
    ]

    result = mock.read(bindings)
    assert isinstance(result, Iterator), "read yields as it goes: an iterator, not a list"
    items = list(result)

    assert [item.index for item in items] == list(range(len(bindings)))
    assert [item.status for item in items] == [EnricherReadStatus.OK, EnricherReadStatus.NOT_FOUND, EnricherReadStatus.ERROR, EnricherReadStatus.ERROR, EnricherReadStatus.OK]
    for item, binding in ((items[0], bindings[0]), (items[4], bindings[4])):
        assert dict(item.values) == {**module.READ_VALUES, "description": item.values["description"]}, "READ_VALUES plus a description"
        assert binding.identifier in item.values["description"], "the description is the binding's own"
        assert item.source_date == module.SOURCE_DATE
        assert set(item.values) <= set(CATALOGUE), "the values are keyed by catalogue voices"
        assert (item.error_code, item.retry_after) == (None, None)
    assert (dict(items[1].values), items[1].error_code) == ({}, None)
    assert items[2].error_code != RATE_LIMITED, "a plain failure is not a refusal for too many requests"
    assert items[2].retry_after is None
    assert (items[3].error_code, items[3].retry_after) == (RATE_LIMITED, module.RATE_LIMITED_RETRY_AFTER)
    assert list(mock.read([])) == []
    print_success("OK, NOT_FOUND, ERROR, RATE_LIMITED with its retry_after, in order")


def test_enricher_rate_limited_is_the_cores_refusal_marker():
    """ENR-3b: a search that is refused raises ``EnricherRateLimited``, a ``RateLimitedError`` the route turns into a 429."""
    assert issubclass(EnricherRateLimited, RateLimitedError)
    assert EnricherRateLimited("refused", retry_after=7.5).retry_after == 7.5
    assert EnricherRateLimited("refused").retry_after is None, "the source named no wait"


def test_mockenrich_has_a_page_and_does_not_search(monkeypatch):
    mock, _module = _mock(monkeypatch)
    binding = EnricherBinding("ISIN", "IE00B4L5Y983")

    url = mock.page_url(binding)

    assert isinstance(url, str) and url.startswith("https://") and binding.identifier in url
    assert mock.supports_search is False
    with pytest.raises(NotImplementedError):
        mock.search("World")


def test_mockenrich_is_withheld_outside_test_mode(monkeypatch):
    """``test_only``: listed and served in test mode (the presence barrier), neither outside it."""
    print_section("mockenrich: test only")
    mock, _module = _mock(monkeypatch)
    assert type(mock).test_only is True
    assert MOCK_CODE in EnricherRegistry.list_plugin_codes(), "barrier: listed in test mode"

    with _production(monkeypatch):
        assert EnricherRegistry.get_plugin(MOCK_CODE) is None
        assert EnricherRegistry.get_plugin_instance(MOCK_CODE) is None
        assert MOCK_CODE not in EnricherRegistry.list_plugin_codes()

    assert EnricherRegistry.get_plugin(MOCK_CODE) is type(mock), "served again once back in test mode"
    print_success("served in test mode, withheld outside it")
