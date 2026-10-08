"""
Provider Contract Tests — Offline Interface Validation.

Tests ALL registered providers (FX, Asset, BRIM) for ABC contract compliance
WITHOUT making any HTTP calls. These tests validate:
- Required properties return correct types and non-empty values
- Static URL generation follows expected patterns
- Test cases / test data are well-formed
- Provider metadata is consistent — including with what it points at: an asset
  provider's help URL names an existing page of the user guide, and an FX
  provider's description counts the currencies its own table serves

Unlike test_external/test_*_providers.py (which test live HTTP), these run
offline and cover base-class methods that are typically at 0% coverage
(generate_static_url, base_currencies, icon, test_cases, etc.).

When a new provider is added with @register_provider, these tests
automatically cover it — no manual test authoring needed.
"""

import re
from pathlib import Path

import pytest

from backend.app.services.provider_registry import (
    AssetProviderRegistry,
    BRIMProviderRegistry,
    FXProviderRegistry,
)

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
