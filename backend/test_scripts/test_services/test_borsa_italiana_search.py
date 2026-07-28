from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from backend.app.db import IdentifierType
from backend.app.services.asset_source_providers import borsa_italiana
from backend.app.services.asset_source_providers.borsa_italiana import BorsaItalianaProvider


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
    assert any(query.upper() == "EURIZON NEXT 2.0 STRATEGIA OBBLIGAZ P" and language == "en" for query, language in calls)
