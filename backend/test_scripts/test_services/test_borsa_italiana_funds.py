"""Borsa Italiana mutual-fund NAV path + resolve_url capability.

Funds are not on the XMIL API: their only NAV source is the fund detail page,
addressed by a Borsa internal code carried in ``provider_params.codice_fondo``.
These tests mock the scraping library (no live Borsa Italiana calls).
"""

from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest

from backend.app.db import IdentifierType
from backend.app.db.models import AssetType
from backend.app.services.asset_source import AssetSearchService, AssetSourceError
from backend.app.services.asset_source_providers import borsa_italiana
from backend.app.services.asset_source_providers.borsa_italiana import BorsaItalianaProvider
from backend.app.services.provider_registry import AssetProviderRegistry

CODE = "2FADB602822"
ISIN = "LU2178929613"


def _fund(data_nav: date, *, codice: str = CODE, isin: str | None = ISIN) -> borsa_italiana.DatiFondo:
    return borsa_italiana.DatiFondo(
        codice=codice,
        nome="Eurizon Next 2.0 Alloc. Divers. 40 P Cap Eur",
        nav=Decimal("121.94"),
        variazione_percentuale=Decimal("0.05"),
        valuta="EUR",
        data_nav=data_nav,
        url=f"https://www.borsaitaliana.it/borsa/fondi/dettaglio/{codice}.html",
        isin=isin,
    )


@pytest.fixture(autouse=True)
def _available(monkeypatch):
    monkeypatch.setattr(borsa_italiana, "BORSA_ITALIANA_AVAILABLE", True)
    monkeypatch.setattr(borsa_italiana, "_get_session", lambda: object())


# ── resolve_url ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_resolve_url_fund_page(monkeypatch):
    """A fund detail URL resolves to the canonical IT+EN set (Italian first, with flags)."""
    monkeypatch.setattr(borsa_italiana, "estrai_codice_da_url", lambda url: CODE, raising=False)
    monkeypatch.setattr(borsa_italiana, "ottieni_dati_fondo_da_url", lambda url, sessione=None: _fund(date(2026, 7, 23)), raising=False)

    items = await BorsaItalianaProvider().resolve_url(f"https://www.borsaitaliana.it/borsa/fondi/dettaglio/{CODE}.html")

    assert isinstance(items, list) and len(items) == 2
    it_item, en_item = items[0], items[1]
    # Italian first, with flag
    assert it_item["provider_params"] == {"codice_fondo": CODE, "language": "it"}
    assert it_item["identifier"] == ISIN
    assert it_item["identifier_type"] == IdentifierType.ISIN
    assert it_item["type"] == "FUND"
    assert it_item["currency"] == "EUR"
    assert "🇮🇹" in it_item["display_name"]
    # English second, with flag, same identifier
    assert en_item["provider_params"]["language"] == "en"
    assert en_item["identifier"] == ISIN
    assert "🇬🇧" in en_item["display_name"]


@pytest.mark.asyncio
async def test_resolve_url_bond_scheda_page(monkeypatch):
    """A stock/bond/ETF scheda URL resolves to the canonical IT+EN set via the ISIN (and MIC) in the URL."""
    monkeypatch.setattr(borsa_italiana, "estrai_codice_da_url", lambda url: None, raising=False)
    # Site-search rediscovery finds nothing: the URL tail alone supplies the MIC.
    monkeypatch.setattr(borsa_italiana, "cerca", lambda q, lingua=None, sessione=None: [], raising=False)
    captured: dict = {}

    def fake_ottieni_scheda(isin, mic=None, lingua="en", sessione=None, platform=None, url_diretto=None):
        captured["isin"], captured["mic"], captured["platform"], captured["url_diretto"] = isin, mic, platform, url_diretto
        return SimpleNamespace(isin=isin, nome="Btp Tf 0,6% Ag31 Eur", valuta="EUR", tipo="obbligazione", url_pagina=None)

    monkeypatch.setattr(borsa_italiana, "ottieni_scheda", fake_ottieni_scheda, raising=False)

    items = await BorsaItalianaProvider().resolve_url("https://www.borsaitaliana.it/borsa/obbligazioni/mot/btp/scheda/IT0005436693-MOTX.html?lang=it")

    assert isinstance(items, list) and len(items) == 2
    # ISIN + market segment (MIC) are read straight from the URL tail; with no
    # platform from the (empty) search, the canonical page is fetched directly.
    assert captured == {
        "isin": "IT0005436693",
        "mic": "MOTX",
        "platform": None,
        "url_diretto": "https://www.borsaitaliana.it/borsa/obbligazioni/mot/btp/scheda/IT0005436693-MOTX.html",
    }
    it_item, en_item = items[0], items[1]
    assert it_item["identifier"] == "IT0005436693"
    assert it_item["identifier_type"] == IdentifierType.ISIN
    assert it_item["type"] == "BOND"
    assert it_item["currency"] == "EUR"
    # the MIC is propagated into provider_params so the saved asset stays routable,
    # plus the page URL actually loaded (kept so get_asset_url never rebuilds a dead link)
    assert it_item["provider_params"] == {"language": "it", "mic": "MOTX", "url": "https://www.borsaitaliana.it/borsa/obbligazioni/mot/btp/scheda/IT0005436693-MOTX.html"}
    assert "🇮🇹" in it_item["display_name"]
    assert en_item["provider_params"]["language"] == "en"
    assert "🇬🇧" in en_item["display_name"]


@pytest.mark.asyncio
async def test_resolve_url_eurotlx_scheda_page(monkeypatch):
    """An EuroTLX canonical URL carries no platform in the URL tail: resolve_url rediscovers
    the authoritative mic/platform via the site search (exact-ISIN hit) and threads them
    into the scheda fetch and the emitted provider_params."""
    monkeypatch.setattr(borsa_italiana, "estrai_codice_da_url", lambda url: None, raising=False)
    isin = "US912810TU25"
    link = f"https://www.borsaitaliana.it/borsa/search/scheda.html?code={isin}&mic=ETLX&platform=TLX&lang=it"

    def fake_cerca(query, lingua=None, sessione=None):
        return [SimpleNamespace(isin=isin, nome="United States Treasury 4% Nv34", tipo="Obbligazione EuroTLX", link=link)]

    captured: dict = {}

    def fake_ottieni_scheda(isin_arg, mic=None, lingua="en", sessione=None, platform=None, url_diretto=None):
        captured["isin"], captured["mic"], captured["platform"], captured["url_diretto"] = isin_arg, mic, platform, url_diretto
        return SimpleNamespace(isin=isin_arg, nome="United States Treasury 4% Nv34", valuta="USD", tipo="obbligazione eurotlx", url_pagina="https://www.borsaitaliana.it/borsa/obbligazioni/eurotlx/scheda/US912810TU25-ETLX.html?lang=it")

    monkeypatch.setattr(borsa_italiana, "cerca", fake_cerca, raising=False)
    monkeypatch.setattr(borsa_italiana, "ottieni_scheda", fake_ottieni_scheda, raising=False)

    items = await BorsaItalianaProvider().resolve_url("https://www.borsaitaliana.it/borsa/obbligazioni/eurotlx/scheda/US912810TU25-ETLX.html")

    # the scheda fetch received the rediscovered market params (platform included),
    # so no direct-URL bypass was needed
    assert captured == {"isin": isin, "mic": "ETLX", "platform": "TLX", "url_diretto": None}
    assert isinstance(items, list) and len(items) == 2
    for item in items:
        assert item["identifier"] == isin
        assert item["type"] == "BOND"
        # currency comes from the scheda (EuroTLX hosts FX-denominated bonds)
        assert item["currency"] == "USD"
        assert item["provider_params"]["mic"] == "ETLX"
        assert item["provider_params"]["platform"] == "TLX"
        # the loaded page URL is carried so get_asset_url returns a working link
        assert item["provider_params"]["url"] == "https://www.borsaitaliana.it/borsa/obbligazioni/eurotlx/scheda/US912810TU25-ETLX.html?lang=it"


@pytest.mark.asyncio
async def test_resolve_url_unrecognised_page_returns_none(monkeypatch):
    """A Borsa URL that is neither a fund page nor an ISIN scheda resolves to None."""
    monkeypatch.setattr(borsa_italiana, "estrai_codice_da_url", lambda url: None, raising=False)

    item = await BorsaItalianaProvider().resolve_url("https://www.borsaitaliana.it/borsa/quotazioni/azioni.html")
    assert item is None


@pytest.mark.asyncio
async def test_resolve_url_off_domain_returns_none():
    """A URL outside borsaitaliana.it is rejected before any fetch."""
    item = await BorsaItalianaProvider().resolve_url("https://finance.yahoo.com/quote/0P0001O3B2.F/")
    assert item is None


@pytest.mark.asyncio
async def test_resolve_url_fallback_to_code_when_no_isin(monkeypatch):
    """When the page has no ISIN, identifier falls back to the code as OTHER (both langs)."""
    monkeypatch.setattr(borsa_italiana, "estrai_codice_da_url", lambda url: CODE, raising=False)
    monkeypatch.setattr(borsa_italiana, "ottieni_dati_fondo_da_url", lambda url, sessione=None: _fund(date(2026, 7, 23), isin=None), raising=False)

    items = await BorsaItalianaProvider().resolve_url(f"https://www.borsaitaliana.it/borsa/fondi/dettaglio/{CODE}.html")
    assert len(items) == 2
    assert items[0]["identifier"] == CODE
    assert items[0]["identifier_type"] == IdentifierType.OTHER
    assert items[0]["provider_params"]["codice_fondo"] == CODE


# ── get_asset_url ───────────────────────────────────────────────────────


def test_get_asset_url_fund_uses_internal_code():
    """A fund item (codice_fondo present) links to the dettaglio page by internal code,
    not the search/scheda page keyed by the ISIN identifier (which is a dead page)."""
    url = BorsaItalianaProvider().get_asset_url(ISIN, IdentifierType.ISIN, {"codice_fondo": CODE, "language": "it"})
    assert url == f"https://www.borsaitaliana.it/borsa/fondi/dettaglio/{CODE}.html?lang=it"


def test_get_asset_url_non_fund_uses_scheda():
    """Non-fund instruments keep the generic search/scheda URL keyed by the identifier."""
    url = BorsaItalianaProvider().get_asset_url("IT0003128367", IdentifierType.ISIN, None)
    assert url == "https://www.borsaitaliana.it/borsa/search/scheda.html?code=IT0003128367&lang=en"


def test_search_serialization_forwards_provider_params_to_url(monkeypatch):
    """Regression: the search serializer must forward ``provider_params`` to get_asset_url,
    otherwise fund items get the dead ISIN search page instead of the dettaglio page.
    Guards the caller (AssetSearchService), not just the provider method."""
    monkeypatch.setattr(AssetProviderRegistry, "get_provider_instance", staticmethod(lambda code, **kw: BorsaItalianaProvider()))

    item = {"identifier": ISIN, "identifier_type": IdentifierType.ISIN, "provider_params": {"codice_fondo": CODE, "language": "it"}}
    url = AssetSearchService._provider_url_for_item("borsa_italiana", item)
    assert url == f"https://www.borsaitaliana.it/borsa/fondi/dettaglio/{CODE}.html?lang=it"


# ── current value: today-only rule ──────────────────────────────────────


@pytest.mark.asyncio
async def test_fund_current_value_today(monkeypatch):
    """When the NAV is dated today, it is returned as the current value."""
    monkeypatch.setattr(borsa_italiana, "ottieni_dati_fondo", lambda codice, sessione=None: _fund(date.today()), raising=False)

    cv = await BorsaItalianaProvider().get_current_value(ISIN, IdentifierType.ISIN, {"codice_fondo": CODE})
    assert cv.value == Decimal("121.94")
    assert cv.currency == "EUR"
    assert cv.as_of_date == date.today()


@pytest.mark.asyncio
async def test_fund_current_value_stale_raises_no_data(monkeypatch):
    """A NAV not dated today must raise NO_DATA (core uses the last-buy estimate)."""
    monkeypatch.setattr(borsa_italiana, "ottieni_dati_fondo", lambda codice, sessione=None: _fund(date.today() - timedelta(days=3)), raising=False)

    with pytest.raises(AssetSourceError) as exc:
        await BorsaItalianaProvider().get_current_value(ISIN, IdentifierType.ISIN, {"codice_fondo": CODE})
    assert exc.value.error_code == "NO_DATA"


# ── history: single NAV point at the real date ──────────────────────────


@pytest.mark.asyncio
async def test_fund_history_single_point_in_range(monkeypatch):
    """History returns exactly one NAV point, at its real (non-today) date."""
    nav_date = date(2026, 7, 23)
    monkeypatch.setattr(borsa_italiana, "ottieni_dati_fondo", lambda codice, sessione=None: _fund(nav_date), raising=False)

    hist = await BorsaItalianaProvider().get_history_value(ISIN, IdentifierType.ISIN, {"codice_fondo": CODE}, date(2026, 1, 1), date(2026, 12, 31))
    assert len(hist.prices) == 1
    assert hist.prices[0].date == nav_date
    assert hist.prices[0].close == Decimal("121.94")
    assert hist.prices[0].currency == "EUR"


@pytest.mark.asyncio
async def test_fund_history_empty_when_out_of_range(monkeypatch):
    """A NAV dated outside the requested window yields no points."""
    monkeypatch.setattr(borsa_italiana, "ottieni_dati_fondo", lambda codice, sessione=None: _fund(date(2020, 1, 1)), raising=False)

    hist = await BorsaItalianaProvider().get_history_value(ISIN, IdentifierType.ISIN, {"codice_fondo": CODE}, date(2026, 1, 1), date(2026, 12, 31))
    assert hist.prices == []


# ── search: fallback when the fund page can't be fetched ─────────────────


@pytest.mark.asyncio
async def test_search_fund_fallback_to_code(monkeypatch):
    """If the fund page fetch fails during search, emit the code as OTHER (still priceable)."""

    def fake_cerca(query, lingua, sessione):
        return [SimpleNamespace(isin=CODE, nome="Eurizon Next 2.0 Alloc. Divers. 40 P", tipo="Common Funds" if lingua == "en" else "Fondi Comuni")]

    def boom(codice, sessione=None):
        raise RuntimeError("fund page unreachable")

    monkeypatch.setattr(borsa_italiana, "cerca", fake_cerca, raising=False)
    monkeypatch.setattr(borsa_italiana, "ottieni_dati_fondo", boom, raising=False)

    results = await BorsaItalianaProvider().search("EURIZON NEXT 2.0 DIVERSIFICATO 40 P")
    assert results, "expected fallback results"
    for item in results:
        assert item["type"] == "FUND"
        assert item["identifier"] == CODE
        assert item["identifier_type"] == IdentifierType.OTHER
        assert item["provider_params"]["codice_fondo"] == CODE


@pytest.mark.asyncio
async def test_search_orders_italian_first_grouped_by_code(monkeypatch):
    """Both language rows of one fund stay adjacent (grouped by internal code) and
    Italian is emitted before English, so sibling funds whose codes differ by a single
    letter never interleave in the picker."""
    code_a, isin_a = "2FADB602822", "LU2178929613"
    code_b, isin_b = "2FADB602823", "LU2178929704"

    def fake_cerca(query, lingua, sessione):
        # Borsa returns both share classes in each language, English requested first.
        return [
            SimpleNamespace(isin=code_a, nome="Eurizon Next 2.0 A", tipo="Common Funds" if lingua == "en" else "Fondi Comuni"),
            SimpleNamespace(isin=code_b, nome="Eurizon Next 2.0 B", tipo="Common Funds" if lingua == "en" else "Fondi Comuni"),
        ]

    def fake_fondo(codice, sessione=None):
        return _fund(date(2026, 7, 23), codice=codice, isin=isin_a if codice == code_a else isin_b)

    monkeypatch.setattr(borsa_italiana, "cerca", fake_cerca, raising=False)
    monkeypatch.setattr(borsa_italiana, "ottieni_dati_fondo", fake_fondo, raising=False)

    results = await BorsaItalianaProvider().search("EURIZON NEXT 2.0")

    order = [(r["provider_params"]["codice_fondo"], r["provider_params"]["language"]) for r in results]
    assert order == [(code_a, "it"), (code_a, "en"), (code_b, "it"), (code_b, "en")]


# ── fund metadata (description enrichment from the fund page) ─────────────


@pytest.mark.asyncio
async def test_fund_metadata_includes_page_sections(monkeypatch):
    """A fund's short description carries name + ISIN + Caratteristiche/Costi entries."""

    dati = SimpleNamespace(
        codice=CODE,
        nome="Eurizon Next 2.0 Alloc. Divers. 40 P Cap Eur",
        valuta="EUR",
        isin=ISIN,
        caratteristiche={"Classe": "P", "Grado di Rischio": "3", "Categoria Assogestioni": "Bilanciati"},
        societa_gestione={},
        costi={"Gestione": "1.3", "Rimborso": "0%"},
    )
    provider = BorsaItalianaProvider()
    monkeypatch.setattr(provider, "_fetch_fund", lambda code: dati)

    item = await provider.fetch_asset_metadata(ISIN, IdentifierType.ISIN, {"codice_fondo": CODE, "language": "it"})

    assert item is not None
    assert item.asset_type == AssetType.FUND
    assert item.identifier_isin == ISIN
    assert item.identifier_other == [CODE]
    assert item.display_name.endswith("🇮🇹")
    sd = item.classification_params.short_description
    assert "ISIN: LU2178929613" in sd
    assert "Classe: P" in sd
    assert "Categoria Assogestioni: Bilanciati" in sd
    assert "Costi — Gestione: 1.3" in sd
    assert "Costi — Rimborso: 0%" in sd


@pytest.mark.asyncio
async def test_fund_metadata_degrades_without_sections(monkeypatch):
    """With an older scraping lib (no section fields) the description falls back to name+ISIN."""
    dati = SimpleNamespace(codice=CODE, nome="Eurizon X", valuta="EUR", isin=ISIN)  # no section attrs
    provider = BorsaItalianaProvider()
    monkeypatch.setattr(provider, "_fetch_fund", lambda code: dati)

    item = await provider.fetch_asset_metadata(ISIN, IdentifierType.ISIN, {"codice_fondo": CODE})

    assert item is not None
    assert item.classification_params.short_description == "Eurizon X | ISIN: LU2178929613"
    assert item.identifier_other == [CODE]
