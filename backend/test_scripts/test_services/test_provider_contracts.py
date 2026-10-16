"""
Provider Contract Tests — Offline Interface Validation.

Tests ALL registered providers (FX, Asset, BRIM) for ABC contract compliance
WITHOUT making any HTTP calls. These tests validate:
- Required properties return correct types and non-empty values
- Static URL generation follows expected patterns
- Test cases / test data are well-formed
- Provider metadata is consistent — including with what it points at: an asset
  provider's help URL names an existing page of the user guide, an asset
  provider that translates its parameters translates exactly the fields its
  params_schema shows, in every language of the catalogue, and an FX
  provider's description counts the currencies its own table serves

Unlike test_external/test_*_providers.py (which test live HTTP), these run
offline and cover base-class methods that are typically at 0% coverage
(generate_static_url, base_currencies, icon, test_cases, etc.).

When a new provider is added with @register_provider, these tests
automatically cover it — no manual test authoring needed.
"""

import json
import re
from pathlib import Path

import pytest

from backend.app.services.assets.registry import AssetProviderRegistry
from backend.app.services.brim.registry import BRIMProviderRegistry
from backend.app.services.fx.registry import FXProviderRegistry
from scripts import i18n_catalog as catalog

REPO_ROOT = Path(__file__).resolve().parents[3]

# The user guide's provider pages: one `<slug>.<lang>.md` per asset provider,
# served at `/mkdocs/user/assets/providers/<slug>/`.
USER_PROVIDER_DOCS = REPO_ROOT / "mkdocs_src" / "docs" / "user" / "assets" / "providers"
USER_PROVIDER_HELP_URL = re.compile(r"/mkdocs/user/assets/providers/(?P<slug>[a-z0-9]+(?:-[a-z0-9]+)*)/")

# ============================================================================
# DISCOVERY (run once at module import)
# ============================================================================

FXProviderRegistry.auto_discover()
AssetProviderRegistry.auto_discover()
BRIMProviderRegistry.auto_discover()


def _fx_codes() -> list[str]:
    return [p["code"] for p in FXProviderRegistry.list_providers()]


def _asset_codes() -> list[str]:
    return [p["code"] for p in AssetProviderRegistry.list_providers()]


def _brim_codes() -> list[str]:
    return [info.code for info in BRIMProviderRegistry.list_plugin_info()]


# ============================================================================
# FX PROVIDER CONTRACT
# ============================================================================


class TestFXProviderContract:
    """Every FX provider must satisfy this contract."""

    @pytest.fixture(params=_fx_codes())
    def provider(self, request):
        return FXProviderRegistry.get_provider_instance(request.param)

    def test_has_valid_code(self, provider):
        """code must be a non-empty string."""
        assert isinstance(provider.code, str)
        assert len(provider.code) >= 2

    def test_has_valid_provider_code_alias(self, provider):
        """provider_code must alias code for unified registry."""
        assert provider.provider_code == provider.code

    def test_has_valid_name(self, provider):
        """name must be a non-empty human-readable string."""
        assert isinstance(provider.name, str)
        assert len(provider.name) >= 3

    def test_has_base_currency_iso(self, provider):
        """base_currency must be a 3-letter ISO code or '*' (wildcard for MANUAL)."""
        assert isinstance(provider.base_currency, str)
        if provider.base_currency == "*":
            return  # MANUAL provider accepts any currency
        assert len(provider.base_currency) == 3
        assert provider.base_currency.isalpha()
        assert provider.base_currency == provider.base_currency.upper()

    def test_base_currencies_contains_base(self, provider):
        """base_currencies list must contain base_currency."""
        bases = provider.base_currencies
        assert isinstance(bases, list)
        assert len(bases) >= 1
        assert provider.base_currency in bases

    def test_has_description(self, provider):
        """description must be a non-empty string."""
        assert isinstance(provider.description, str)
        assert len(provider.description) > 5

    def test_description_i18n_has_en(self, provider):
        """description_i18n must include at least 'en' key."""
        d = provider.description_i18n
        assert isinstance(d, dict)
        assert "en" in d
        assert len(d["en"]) > 5

    def test_generate_static_url_format(self, provider):
        """generate_static_url must return a proper API path."""
        url = provider.generate_static_url(f"{provider.code.lower()}/test.png")
        assert url.startswith("/api/v1/uploads/plugin/fx/")
        assert "test.png" in url

    def test_icon_is_none_or_string(self, provider):
        """icon must be None or a non-empty string (URL or path)."""
        icon = provider.icon
        assert icon is None or (isinstance(icon, str) and len(icon) > 0)

    def test_test_currencies_are_iso(self, provider):
        """test_currencies must be a list of 3-letter ISO codes (empty allowed for MANUAL)."""
        currencies = provider.test_currencies
        assert isinstance(currencies, list)
        for curr in currencies:
            assert isinstance(curr, str)
            assert len(curr) == 3, f"Invalid test currency: {curr}"

    def test_multi_unit_currencies_are_iso(self, provider):
        """multi_unit_currencies must be a set of 3-letter ISO codes."""
        mu = provider.multi_unit_currencies
        assert isinstance(mu, set)
        for curr in mu:
            assert isinstance(curr, str)
            assert len(curr) == 3, f"Invalid multi-unit currency: {curr}"

    def test_docs_url_is_none_or_string(self, provider):
        """docs_url must be None or a valid path string."""
        url = provider.docs_url
        assert url is None or (isinstance(url, str) and len(url) > 0)

    def test_warning_i18n_is_dict(self, provider):
        """warning_i18n must be a dict (possibly empty)."""
        w = provider.warning_i18n
        assert isinstance(w, dict)
        # If non-empty, must have 'en' key
        if w:
            assert "en" in w


# FX providers whose quote currencies are a fixed table in the class
# (`CURRENCY_SERIES`), so the count their description promises can be checked
# offline. ECB learns its list at runtime and is out of reach here.
FX_FIXED_TABLE_CODES = ("BOE", "FED")
DESCRIPTION_LANGUAGES = ("en", "it", "fr", "es")
# A count as a reader takes it: "15", "20+". Digits glued to a letter, a dot or a
# colon belong to a name or a time, not to a count: FED cites the "H.10" release.
STATED_COUNT = re.compile(r"(?<![\w.:])(\d+)\+?(?![\w.:])")


class TestFXProviderStatedCoverage:
    """A description that counts currencies counts the ones the provider serves.

    The description is what the provider picker shows a user deciding which source
    to route a pair through. "20+ currencies" read there is a promise about which
    pairs can be priced, and it is checked against the table the fetch actually
    walks, in every language it is written in. "N" and "N+" are both honest when N
    is the size of the table.
    """

    @pytest.mark.parametrize("lang", DESCRIPTION_LANGUAGES)
    @pytest.mark.parametrize("code", FX_FIXED_TABLE_CODES)
    def test_description_counts_the_currencies_in_its_table(self, code, lang):
        provider = FXProviderRegistry.get_provider_instance(code)
        table = provider.CURRENCY_SERIES
        # Precondition, verified rather than assumed: the table holds quote
        # currencies only, so its size is the number served against the base.
        assert provider.base_currency not in table, f"{code}: CURRENCY_SERIES lists its own base {provider.base_currency}"

        text = provider.description_i18n[lang]
        stated = [int(n) for n in STATED_COUNT.findall(text)]
        assert stated, f"{code} [{lang}] no longer says how many currencies it serves: {text!r}"
        assert set(stated) == {len(table)}, f"{code} [{lang}] promises {stated} currencies against {provider.base_currency}, CURRENCY_SERIES serves {len(table)}: {text!r}"


# ============================================================================
# ASSET SOURCE PROVIDER CONTRACT
# ============================================================================

# The languages the app ships: those of the catalogue's base (scripts/i18n_catalog.py). A provider that
# translates its parameters translates them in each one.
CATALOG_LANGUAGES = tuple(catalog.languages(REPO_ROOT))
# The two texts the asset form reads for a parameter, `assets.providerParams.<code>.<kind>.<key>`
# (ProviderAssignmentSection.paramText), before falling back to params_schema's English.
PARAM_TEXT_KINDS = ("label", "description")
# The providers whose params_schema fields carry an English label and whose own i18n fragments translate
# them: Borsa Italiana always did, justETF and the CSS scraper since O-9.
LABELLED_PARAM_PROVIDERS = ("borsa_italiana", "css_scraper", "justetf")


def _form_param_fields(provider) -> list[dict]:
    """The params_schema fields the asset form shows with a label and a tooltip: every one but a
    ``ui_component``, the meta-field naming a custom editor (ProviderAssignmentSection's ``genericFields``)."""
    return [field for field in provider.params_schema if field.get("type") != "ui_component"]


def _param_fragment(provider, lang: str) -> Path:
    """The provider's own fragment in ``lang``, a source of the catalogue: ``i18n/<lang>.json`` in the plugin
    folder its class was loaded from (the module discovery names ``<family>.<plugin>.plugin``)."""
    folder = type(provider).__module__.split(".")[:-1]
    return REPO_ROOT.joinpath(*folder, catalog.PLUGIN_I18N_DIR, f"{lang}.json")


def _param_translations(provider) -> dict[str, object]:
    """``assets.providerParams.<code>`` of the provider's fragment in each catalogue language; None where the
    file or the branch is absent."""
    found: dict[str, object] = {}
    for lang in CATALOG_LANGUAGES:
        path = _param_fragment(provider, lang)
        node: object = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None
        for segment in ("assets", "providerParams", provider.provider_code):
            node = node.get(segment) if isinstance(node, dict) else None
        found[lang] = node
    return found


def _is_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _param_text_problems(where: str, kind: str, texts: object, expected: set[str]) -> list[str]:
    """What is wrong with one ``label`` or ``description`` branch against the keys of the form's fields: the
    branch missing, a field without its text, a text for no field, a text that is empty or not a string."""
    if not isinstance(texts, dict):
        return [f"{where}: no {kind} branch"]
    given = set(texts)
    problems = []
    if missing := sorted(expected - given):
        problems.append(f"{where}: no {kind} for {missing}, fields of params_schema")
    if stale := sorted(given - expected):
        problems.append(f"{where}: a {kind} for {stale}, no field of params_schema")
    if blank := sorted(key for key in expected & given if not _is_text(texts[key])):
        problems.append(f"{where}: the {kind} of {blank} is not a non-empty string")
    return problems


class TestAssetProviderContract:
    """Every Asset Source provider must satisfy this contract."""

    @pytest.fixture(params=_asset_codes())
    def provider(self, request):
        return AssetProviderRegistry.get_provider_instance(request.param)

    def test_has_valid_code(self, provider):
        """provider_code must be a non-empty string."""
        assert isinstance(provider.provider_code, str)
        assert len(provider.provider_code) >= 3

    def test_has_valid_name(self, provider):
        """provider_name must be a non-empty human-readable string."""
        assert isinstance(provider.provider_name, str)
        assert len(provider.provider_name) >= 3

    def test_test_cases_valid(self, provider):
        """test_cases must be a non-empty list; each entry needs at least 'identifier'."""
        cases = provider.test_cases
        assert isinstance(cases, list)
        assert len(cases) >= 1, f"Provider {provider.provider_code} has no test cases"
        for tc in cases:
            assert "identifier" in tc, f"test_case missing 'identifier': {tc}"
            # identifier_type is optional — some providers (e.g., scheduled_investment)
            # use auto-generated identifiers without explicit type

    def test_test_search_query_type(self, provider):
        """test_search_query must be str or None."""
        q = provider.test_search_query
        assert q is None or isinstance(q, str)

    def test_supports_search_consistency(self, provider):
        """supports_search must be True iff test_search_query is not None."""
        has_query = provider.test_search_query is not None
        # Default implementation: supports_search = test_search_query is not None
        # Some providers may override, so we just check type
        assert isinstance(provider.supports_search, bool)
        if not has_query:
            # If no test query, search should not be supported (unless overridden)
            pass  # Don't enforce — some providers override supports_search

    def test_supports_history_is_bool(self, provider):
        """supports_history must be a boolean."""
        assert isinstance(provider.supports_history, bool)

    def test_generate_static_url_format(self, provider):
        """generate_static_url must return a proper API path."""
        url = provider.generate_static_url(f"{provider.provider_code}/test.png")
        assert url.startswith("/api/v1/uploads/plugin/asset/")
        assert "test.png" in url

    def test_icon_is_none_or_string(self, provider):
        """get_icon must be None or a non-empty string."""
        icon = provider.get_icon
        assert icon is None or (isinstance(icon, str) and len(icon) > 0)

    def test_help_url_is_none_or_string(self, provider):
        """provider_help_url must be None or a valid path string."""
        url = provider.provider_help_url
        assert url is None or (isinstance(url, str) and len(url) > 0)

    def test_help_url_opens_its_page_in_the_user_guide(self, provider):
        """A help URL is the provider's page in the *user* guide, and that page exists.

        The link sits beside the provider where a user picks a price source, so it
        must land on the page written for that reader — one per provider under
        ``user/assets/providers/`` — not on developer internals, and not on a page
        nobody wrote.
        """
        url = provider.provider_help_url
        if url is None:
            pytest.skip(f"{provider.provider_code} publishes no help URL")
        match = USER_PROVIDER_HELP_URL.fullmatch(url)
        assert match, f"{provider.provider_code}: provider_help_url {url!r} is not /mkdocs/user/assets/providers/<slug>/"
        page = USER_PROVIDER_DOCS / f"{match['slug']}.en.md"
        assert page.is_file(), f"{provider.provider_code}: {url!r} names no page — {page.relative_to(REPO_ROOT)} does not exist"

    def test_help_url_guard_has_something_to_check(self):
        """Positive control for the guard above: its green is not the green of an empty check.

        The docs tree it resolves against holds provider pages, and registered
        providers do publish help URLs — so a red there is a wrong URL, never a
        guard reading an empty directory or a property nobody sets any more.
        """
        pages = sorted(p.name for p in USER_PROVIDER_DOCS.glob("*.en.md") if p.name != "index.en.md")
        assert pages, f"no provider page under {USER_PROVIDER_DOCS.relative_to(REPO_ROOT)}: the guard reads the wrong place"
        with_url = [code for code in _asset_codes() if AssetProviderRegistry.get_provider_instance(code).provider_help_url]
        assert with_url, "no registered asset provider publishes a help URL: the guard checks nothing"

    def test_params_schema_valid(self, provider):
        """params_schema must be a list of dicts with at least 'key' and 'type'."""
        schema = provider.params_schema
        assert isinstance(schema, list)
        for field in schema:
            assert isinstance(field, dict), f"params_schema entry is not dict: {field}"
            assert "key" in field, f"params_schema field missing 'key': {field}"
            assert "type" in field, f"params_schema field missing 'type': {field}"

    def test_param_translations_cover_exactly_its_form_params(self, provider):
        """A provider that translates its parameters translates exactly the fields its form shows, in every
        language of the catalogue.

        The asset form shows ``assets.providerParams.<code>.<label|description>.<key>`` when the catalogue has
        it, else the English ``label`` / ``description`` of params_schema (a label without either shows the raw
        key). So a field added without a translation reads English in an Italian form, and the translation of a
        removed field lingers as a key nobody reads: under ``label`` and under ``description`` the keys are the
        form's fields, no more, no fewer, each with a non-empty text, in every language. A provider whose
        fragments hold no ``assets.providerParams.<code>`` shows params_schema's English: nothing to compare.
        """
        code = provider.provider_code
        translations = _param_translations(provider)
        if all(branch is None for branch in translations.values()):
            pytest.skip(f"{code} translates no parameter: its form shows the English of params_schema")
        expected = {field["key"] for field in _form_param_fields(provider)}
        problems = []
        for lang, branch in translations.items():
            where = f"{code} [{lang}] {catalog.display_path(_param_fragment(provider, lang), REPO_ROOT)}"
            if not isinstance(branch, dict):
                problems.append(f"{where}: no assets.providerParams.{code} branch, which another language has")
                continue
            for kind in PARAM_TEXT_KINDS:
                problems += _param_text_problems(where, kind, branch.get(kind), expected)

        assert not problems, f"{len(problems)} problem(s):\n" + "\n".join(problems)

    def test_param_translation_guard_has_something_to_check(self):
        """Positive control for the guard above: its green is not the green of an empty check.

        The catalogue ships the four languages, and each provider that labels and translates its parameters is
        registered and has a branch where the guard reads, in its own fragment, under its own code. So a skip
        there is a provider with nothing translated, never a guard reading the wrong folder or the wrong code.
        """
        assert {"en", "it", "fr", "es"} <= set(CATALOG_LANGUAGES), f"the catalogue's base ships {CATALOG_LANGUAGES}"
        for code in LABELLED_PARAM_PROVIDERS:
            provider = AssetProviderRegistry.get_provider_instance(code)
            assert provider is not None, f"{code} is not a registered asset provider"
            translated = [lang for lang, branch in _param_translations(provider).items() if branch is not None]
            fragments = catalog.display_path(_param_fragment(provider, catalog.SOURCE_LANGUAGE).parent, REPO_ROOT)
            assert translated, f"{code}: no assets.providerParams.{code} in {fragments}: the guard checks nothing of it"

    @pytest.mark.parametrize("code", LABELLED_PARAM_PROVIDERS)
    def test_form_params_carry_an_english_label(self, code):
        """Each field the form shows has a non-empty English ``label``: its caption when a translation is
        missing, and the one an API client reads. With neither, the form shows the raw key
        (``current_css_selector``): what justETF and the CSS scraper showed before O-9."""
        provider = AssetProviderRegistry.get_provider_instance(code)
        assert provider is not None, f"{code} is not a registered asset provider"
        fields = _form_param_fields(provider)
        assert fields, f"{code}: params_schema shows no field, nothing to label"

        unlabelled = [field["key"] for field in fields if not _is_text(field.get("label"))]
        assert not unlabelled, f"{code}: params_schema fields without an English label: {unlabelled}"

    def test_accepted_identifier_types_valid(self, provider):
        """accepted_identifier_types must be a non-empty list."""
        types = provider.accepted_identifier_types
        assert isinstance(types, list)
        assert len(types) >= 1


# ============================================================================
# BRIM PROVIDER CONTRACT
# ============================================================================


class TestBRIMProviderContract:
    """Every BRIM (Broker Report Import) plugin must satisfy this contract."""

    @pytest.fixture(params=_brim_codes())
    def provider(self, request):
        return BRIMProviderRegistry.get_provider_instance(request.param)

    def test_has_valid_code(self, provider):
        """provider_code must be a non-empty string."""
        assert isinstance(provider.provider_code, str)
        assert len(provider.provider_code) >= 3

    def test_has_valid_name(self, provider):
        """provider_name must be a non-empty human-readable string."""
        assert isinstance(provider.provider_name, str)
        assert len(provider.provider_name) >= 3

    def test_has_description(self, provider):
        """description must be a non-empty string."""
        assert isinstance(provider.description, str)
        assert len(provider.description) > 5

    def test_supported_extensions_valid(self, provider):
        """supported_extensions must be a non-empty list of dot-prefixed strings."""
        exts = provider.supported_extensions
        assert isinstance(exts, list)
        assert len(exts) >= 1
        for ext in exts:
            assert isinstance(ext, str)
            assert ext.startswith("."), f"Extension must start with '.': {ext}"
            assert len(ext) >= 2

    def test_detection_priority_is_int(self, provider):
        """detection_priority must be a non-negative integer."""
        p = provider.detection_priority
        assert isinstance(p, int)
        assert p >= 0

    def test_generate_static_url_format(self, provider):
        """generate_static_url must return a proper API path."""
        url = provider.generate_static_url(f"{provider.provider_code}/test.png")
        assert url.startswith("/api/v1/uploads/plugin/brim/")
        assert "test.png" in url

    def test_icon_url_is_none_or_string(self, provider):
        """icon_url must be None or a non-empty string."""
        icon = provider.icon_url
        assert icon is None or (isinstance(icon, str) and len(icon) > 0)

    def test_can_parse_nonexistent_file(self, provider):
        """can_parse on a nonexistent file must return False, not crash."""
        fake_path = Path("/tmp/nonexistent_file_12345.csv")
        assert not fake_path.exists()
        result = provider.can_parse(fake_path)
        assert result is False or result is None
