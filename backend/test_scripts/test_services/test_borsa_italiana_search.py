from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from backend.app.db import IdentifierType
from backend.app.db.models import AssetType
from backend.app.services.asset_source_providers.borsa_italiana import plugin as borsa_italiana
from backend.app.services.asset_source_providers.borsa_italiana.plugin import BorsaItalianaProvider
from backend.app.services.plugin_settings.contract import BoundSettings
from backend.app.services.plugin_settings.fields import SettingScope, SettingType


def _available(monkeypatch):
    """Stub library availability + HTTP session (no network, like the other BI tests)."""
    monkeypatch.setattr(borsa_italiana, "BORSA_ITALIANA_AVAILABLE", True)
    monkeypatch.setattr(borsa_italiana, "_get_session", lambda: object())


@pytest.mark.asyncio
async def test_borsa_italiana_search_retries_fund_abbreviations(monkeypatch):
    """Full fund names should retry Borsa's abbreviated title index.

    Fund search hits carry the Borsa **internal code** in the ``isin`` field; the
    provider then fetches the fund page once per code (``ottieni_dati_fondo``) to
    recover the **real ISIN** and expose the internal code in ``provider_params``.
    """
    calls: list[tuple[str, str]] = []
    fund_fetches: list[str] = []

    def fake_cerca(query: str, lingua: str, sessione):
        calls.append((query, lingua))
        if "OBBLIGAZ P" not in query.upper():
            return []
        return [
            SimpleNamespace(
                isin="2FADB603927",  # Borsa internal code, not a real ISIN
                nome="Eurizon Next 2.0 Strategia Obbligaz. P Cap Eur",
                tipo="Common Funds" if lingua == "en" else "Fondi Comuni",
            )
        ]

    def fake_ottieni_dati_fondo(codice: str, sessione=None):
        fund_fetches.append(codice)
        return borsa_italiana.DatiFondo(
            codice=codice,
            nome="Eurizon Next 2.0 Strategia Obbligaz. P Cap Eur",
            nav=Decimal("105.5"),
            variazione_percentuale=Decimal("0.1"),
            valuta="EUR",
            data_nav=date(2026, 7, 23),
            url=f"https://www.borsaitaliana.it/borsa/fondi/dettaglio/{codice}.html",
            isin="IT0005TESTFND",
        )

    monkeypatch.setattr(borsa_italiana, "BORSA_ITALIANA_AVAILABLE", True)
    monkeypatch.setattr(borsa_italiana, "_get_session", lambda: object())
    monkeypatch.setattr(borsa_italiana, "cerca", fake_cerca, raising=False)
    monkeypatch.setattr(borsa_italiana, "ottieni_dati_fondo", fake_ottieni_dati_fondo, raising=False)

    results = await BorsaItalianaProvider().search("EURIZON NEXT 2.0 - STRATEGIA OBBLIGAZIONARIA P")

    assert [item["provider_params"]["language"] for item in results] == ["it", "en"]
    # identifier is now the REAL ISIN from the fund page, not the internal code
    assert all(item["identifier"] == "IT0005TESTFND" for item in results)
    assert all(item["identifier_type"] == IdentifierType.ISIN for item in results)
    assert all(item["type"] == "FUND" for item in results)
    # the internal code is preserved in provider_params for NAV pricing
    assert all(item["provider_params"]["codice_fondo"] == "2FADB603927" for item in results)
    # the fund page is fetched only once per code (in-search cache), not per language
    assert fund_fetches == ["2FADB603927"]
    # A single on-site fetch (Italian) is performed; the abbreviated title variant must still be tried.
    assert all(language == "it" for _query, language in calls)
    assert any(query.upper() == "EURIZON NEXT 2.0 STRATEGIA OBBLIGAZ P" for query, _language in calls)


# ── market routing (mic/platform) and result filtering ───────────────────────


@pytest.mark.asyncio
async def test_search_eurotlx_bond_carries_market_params(monkeypatch):
    """An EuroTLX bond hit: mic/platform are parsed from the site link into
    provider_params (both language rows); currency stays unknown at search time."""
    _available(monkeypatch)
    isin = "US912810TU25"
    link = f"https://www.borsaitaliana.it/borsa/search/scheda.html?code={isin}&mic=ETLX&platform=TLX&lang=it"
    results = [SimpleNamespace(isin=isin, nome="United States Treasury 4% Nv34", tipo="Obbligazione EuroTLX", link=link)]
    monkeypatch.setattr(borsa_italiana, "cerca", lambda q, lingua=None, sessione=None: results, raising=False)

    items = await BorsaItalianaProvider().search("US912810TU25")

    assert len(items) == 2  # IT + EN fan-out
    assert {it["identifier"] for it in items} == {isin}
    assert {it["type"] for it in items} == {AssetType.BOND.value}
    assert {it["currency"] for it in items} == {None}
    for item in items:
        assert item["provider_params"]["mic"] == "ETLX"
        assert item["provider_params"]["platform"] == "TLX"


@pytest.mark.asyncio
async def test_search_excludes_indices(monkeypatch):
    """Indices are benchmarks, not purchasable instruments: excluded entirely."""
    _available(monkeypatch)
    results = [
        SimpleNamespace(
            isin="IDX00FTSEMIB",
            nome="FTSE MIB",
            tipo="Indice",
            link="https://www.borsaitaliana.it/borsa/search/scheda.html?code=IDX00FTSEMIB&mic=IDX&lang=it",
        )
    ]
    monkeypatch.setattr(borsa_italiana, "cerca", lambda q, lingua=None, sessione=None: results, raising=False)

    assert await BorsaItalianaProvider().search("FTSE MIB") == []


@pytest.mark.asyncio
async def test_search_skips_results_without_market_params(monkeypatch):
    """No-dead-results rule: a non-fund result whose link carries no mic would produce
    an unresolvable URL — skipped; a sibling result with a mic is still emitted."""
    _available(monkeypatch)
    results = [
        SimpleNamespace(isin="IT0000000001", nome="Dead Instrument", tipo="Azione", link=None),
        SimpleNamespace(
            isin="IT0003128367",
            nome="ENEL",
            tipo="Azione",
            link="https://www.borsaitaliana.it/borsa/search/scheda.html?code=IT0003128367&mic=MTAA&lang=it",
        ),
    ]
    monkeypatch.setattr(borsa_italiana, "cerca", lambda q, lingua=None, sessione=None: results, raising=False)

    items = await BorsaItalianaProvider().search("ENEL")

    assert len(items) == 2  # only the live instrument, IT + EN
    assert {it["identifier"] for it in items} == {"IT0003128367"}


@pytest.mark.asyncio
async def test_search_closed_end_fund_uses_isin_path(monkeypatch):
    """Closed-end funds (MIV) have a real ISIN + mic: they price like any listed
    instrument (type FUND via the ISIN path), NOT via the NAV-by-code path."""
    _available(monkeypatch)
    isin = "IT0005532981"
    link = f"https://www.borsaitaliana.it/borsa/search/scheda.html?code={isin}&mic=MIVX&lang=it"
    results = [SimpleNamespace(isin=isin, nome="Closed Fund X", tipo="Fondo Chiuso", link=link)]
    monkeypatch.setattr(borsa_italiana, "cerca", lambda q, lingua=None, sessione=None: results, raising=False)
    # the NAV path must not be touched for a closed-end fund
    fondo_calls: list[str] = []
    monkeypatch.setattr(borsa_italiana, "ottieni_dati_fondo", lambda codice, sessione=None: fondo_calls.append(codice), raising=False)

    items = await BorsaItalianaProvider().search("CLOSED FUND X")

    assert len(items) == 2
    for item in items:
        assert item["identifier"] == isin
        assert item["identifier_type"] == IdentifierType.ISIN
        assert item["type"] == AssetType.FUND.value
        assert item["provider_params"]["mic"] == "MIVX"
        assert "codice_fondo" not in item["provider_params"]
    assert fondo_calls == []


# ── the user's preferred language (CP11a): search and resolve_url's two pages ─

FUND_CODE, FUND_ISIN, FUND_NAME = "2FADB603927", "IT0005TESTFND", "Probe Fund P Cap Eur"
STOCK_ISIN, STOCK_NAME = "IT0003128367", "ENEL"
#: The site's own link of a listed instrument: its query string carries the market, as _parse_link_market_params reads it.
STOCK_LINK = f"https://www.borsaitaliana.it/borsa/search/scheda.html?code={STOCK_ISIN}&mic=MTAA&lang=it"
STOCK_PAGE = f"https://www.borsaitaliana.it/borsa/azioni/scheda/{STOCK_ISIN}-MTAA.html"
FLAGS = BorsaItalianaProvider.LANGUAGE_FLAGS

#: (the preference bound, or None for an instance nobody configured; the languages emitted, in their order)
_PREFERENCES = [
    pytest.param("it", ("it",), id="italian"),
    pytest.param("en", ("en",), id="english"),
    pytest.param("all", ("it", "en"), id="both-languages"),
    pytest.param(None, ("it", "en"), id="unbound"),
]


def _provider(preferred: str | None) -> BorsaItalianaProvider:
    """A provider with ``preferred_language`` bound as the core binds it before a search; ``None``: nobody configured it."""
    provider = BorsaItalianaProvider()
    if preferred is not None:
        provider.bind_settings(BoundSettings(BorsaItalianaProvider.settings_fields, {"preferred_language": preferred}, {}))
    return provider


def _fund_page(codice: str, sessione=None):
    """The fund detail page of ``codice``: the real ISIN and the NAV."""
    return borsa_italiana.DatiFondo(
        codice=codice,
        nome=FUND_NAME,
        nav=Decimal("105.5"),
        variazione_percentuale=Decimal("0.1"),
        valuta="EUR",
        data_nav=date(2026, 7, 23),
        url=f"https://www.borsaitaliana.it/borsa/fondi/dettaglio/{codice}.html",
        isin=FUND_ISIN,
    )


def _fund_rows(languages: tuple[str, ...]) -> list[tuple]:
    return [(FUND_ISIN, f"{FUND_NAME} {FLAGS[language]}", {"codice_fondo": FUND_CODE, "language": language}) for language in languages]


def test_preferred_language_is_one_user_select_of_both_italian_and_english():
    (declared,) = BorsaItalianaProvider.settings_fields

    assert (declared.key, declared.type, declared.scope, declared.secret, declared.required, declared.default) == ("preferred_language", SettingType.SELECT, SettingScope.USER, False, False, "all")
    assert [(option.value, option.label_key) for option in declared.options] == [
        ("all", "pluginSettings.asset.borsa_italiana.option.preferred_language.all"),
        ("it", "pluginSettings.asset.borsa_italiana.option.preferred_language.it"),
        ("en", "pluginSettings.asset.borsa_italiana.option.preferred_language.en"),
    ]
    assert (declared.label_key, declared.description_key) == ("pluginSettings.asset.borsa_italiana.label.preferred_language", "pluginSettings.asset.borsa_italiana.description.preferred_language")


@pytest.mark.parametrize(("preferred", "languages"), _PREFERENCES)
@pytest.mark.asyncio
async def test_search_emits_the_preferred_language_for_a_fund_and_a_listed_instrument(monkeypatch, preferred, languages):
    """One row per emitted language, instrument by instrument — a fund priced by its NAV, a stock routed by the mic of
    its link; the site is still searched in Italian whatever the preference (decision N8)."""
    _available(monkeypatch)
    asked: list[str] = []

    def fake_cerca(query: str, lingua: str, sessione):
        asked.append(lingua)
        return [
            SimpleNamespace(isin=FUND_CODE, nome=FUND_NAME, tipo="Fondi Comuni", link=None),
            SimpleNamespace(isin=STOCK_ISIN, nome=STOCK_NAME, tipo="Azione", link=STOCK_LINK),
        ]

    monkeypatch.setattr(borsa_italiana, "cerca", fake_cerca, raising=False)
    monkeypatch.setattr(borsa_italiana, "ottieni_dati_fondo", _fund_page, raising=False)

    items = await _provider(preferred).search("ENEL")

    assert borsa_italiana._parse_link_market_params(STOCK_LINK) == ("MTAA", None), "barrier: the link routes the stock to its market"
    stock_rows = [(STOCK_ISIN, f"{STOCK_NAME} {FLAGS[language]}", {"language": language, "mic": "MTAA", "url": STOCK_LINK}) for language in languages]
    assert [(item["identifier"], item["display_name"], item["provider_params"]) for item in items] == _fund_rows(languages) + stock_rows
    assert [item["type"] for item in items] == [AssetType.FUND.value] * len(languages) + [AssetType.STOCK.value] * len(languages)
    assert asked and set(asked) == {"it"}, f"the site is searched in Italian only, got {asked}"


@pytest.mark.parametrize(("preferred", "languages"), _PREFERENCES)
def test_a_resolved_fund_page_emits_the_preferred_language(preferred, languages):
    """``resolve_url``'s fund page gives the rows a search would: the preferred language, or both, Italian first."""
    items = _provider(preferred)._fund_search_items_all_langs(_fund_page(FUND_CODE))

    assert [(item["identifier"], item["display_name"], item["provider_params"]) for item in items] == _fund_rows(languages)


@pytest.mark.parametrize(("preferred", "languages"), _PREFERENCES)
def test_a_resolved_scheda_page_emits_the_preferred_language(monkeypatch, preferred, languages):
    """``resolve_url``'s scheda page, read once and in Italian whatever the preference: one row per emitted language."""
    _available(monkeypatch)
    pages: list[tuple] = []

    def fake_scheda(isin, mic=None, lingua="it", sessione=None, platform=None, url_diretto=None):
        pages.append((isin, mic, lingua))
        return SimpleNamespace(isin=STOCK_ISIN, nome=STOCK_NAME, tipo="Azione", url_pagina=STOCK_PAGE)

    monkeypatch.setattr(borsa_italiana, "ottieni_scheda", fake_scheda, raising=False)
    monkeypatch.setattr(borsa_italiana, "_price_api_currency", lambda identifier, mic: "EUR")

    items = _provider(preferred)._scheda_search_items_all_langs(STOCK_ISIN, "MTAA")

    expected = [(STOCK_ISIN, f"{STOCK_NAME} {FLAGS[language]}", "EUR", AssetType.STOCK.value, {"language": language, "mic": "MTAA", "url": STOCK_PAGE}) for language in languages]
    assert [(item["identifier"], item["display_name"], item["currency"], item["type"], item["provider_params"]) for item in items] == expected
    assert pages == [(STOCK_ISIN, "MTAA", "it")]
