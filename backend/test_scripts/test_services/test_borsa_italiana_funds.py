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
from backend.app.services.asset_source import AssetSourceError
from backend.app.services.asset_source_providers import borsa_italiana
from backend.app.services.asset_source_providers.borsa_italiana import BorsaItalianaProvider

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
    """A fund detail URL resolves to a search-item with the real ISIN + code."""
    monkeypatch.setattr(borsa_italiana, "estrai_codice_da_url", lambda url: CODE, raising=False)
    monkeypatch.setattr(borsa_italiana, "ottieni_dati_fondo_da_url", lambda url, sessione=None: _fund(date(2026, 7, 23)), raising=False)

    item = await BorsaItalianaProvider().resolve_url(f"https://www.borsaitaliana.it/borsa/fondi/dettaglio/{CODE}.html")

    assert item is not None
    assert item["identifier"] == ISIN
    assert item["identifier_type"] == IdentifierType.ISIN
    assert item["type"] == "FUND"
    assert item["currency"] == "EUR"
    assert item["provider_params"] == {"codice_fondo": CODE, "language": "it"}


@pytest.mark.asyncio
async def test_resolve_url_non_fund_returns_none(monkeypatch):
    """A Borsa URL that is not a fund page (no extractable code) resolves to None."""
    monkeypatch.setattr(borsa_italiana, "estrai_codice_da_url", lambda url: None, raising=False)

    item = await BorsaItalianaProvider().resolve_url("https://www.borsaitaliana.it/borsa/azioni/scheda/IT0003128367.html")
    assert item is None


@pytest.mark.asyncio
async def test_resolve_url_off_domain_returns_none():
    """A URL outside borsaitaliana.it is rejected before any fetch."""
    item = await BorsaItalianaProvider().resolve_url("https://finance.yahoo.com/quote/0P0001O3B2.F/")
    assert item is None


@pytest.mark.asyncio
async def test_resolve_url_fallback_to_code_when_no_isin(monkeypatch):
    """When the page has no ISIN, identifier falls back to the code as OTHER."""
    monkeypatch.setattr(borsa_italiana, "estrai_codice_da_url", lambda url: CODE, raising=False)
    monkeypatch.setattr(borsa_italiana, "ottieni_dati_fondo_da_url", lambda url, sessione=None: _fund(date(2026, 7, 23), isin=None), raising=False)

    item = await BorsaItalianaProvider().resolve_url(f"https://www.borsaitaliana.it/borsa/fondi/dettaglio/{CODE}.html")
    assert item["identifier"] == CODE
    assert item["identifier_type"] == IdentifierType.OTHER
    assert item["provider_params"]["codice_fondo"] == CODE


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
