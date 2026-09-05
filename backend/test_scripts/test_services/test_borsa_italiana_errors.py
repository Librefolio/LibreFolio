"""Borsa Italiana provider — error and edge paths (no network, no DB, no server).

The happy paths for search, fund NAV and resolve_url live in
``test_borsa_italiana_search.py`` / ``test_borsa_italiana_funds.py``. This file
fills the error and branch gaps those leave open: the pure inference helpers,
the library-error → AssetSourceError mappings for current value / history /
fund NAV, the ISIN scheda metadata assembly and its failure, and the search /
resolve_url failure branches. Every scraping-library call is monkeypatched, so
no request reaches borsaitaliana.it and each assertion is exact.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest
from borsa_italiana_scraping import StrumentoNonRisolto

from backend.app.db import IdentifierType
from backend.app.db.models import AssetType, ProviderInputType
from backend.app.schemas.provider import FAVolumeKind
from backend.app.services.asset_source import AssetSourceError
from backend.app.services.asset_source_providers import borsa_italiana as bi
from backend.app.services.asset_source_providers.borsa_italiana import BorsaItalianaProvider

# Captured at import, before the autouse fixture stubs the module name, so the
# lazy-init contract of the real _get_session stays testable.
_REAL_GET_SESSION = bi._get_session


@pytest.fixture(autouse=True)
def _available(monkeypatch):
    monkeypatch.setattr(bi, "BORSA_ITALIANA_AVAILABLE", True)
    monkeypatch.setattr(bi, "_get_session", lambda: object())


def _provider() -> BorsaItalianaProvider:
    return BorsaItalianaProvider()


# ── builders for the scraping library's return shapes ───────────────────────


def _prezzo(prezzo: Decimal, valuta: str, data: date):
    return SimpleNamespace(prezzo=prezzo, valuta=valuta, data=data)


def _punto(data, *, apertura=None, massimo=None, minimo=None, chiusura=None, ultimo=None, volume=None):
    return SimpleNamespace(data=data, apertura=apertura, massimo=massimo, minimo=minimo, chiusura=chiusura, ultimo=ultimo, volume=volume)


def _storico(punti, valuta: str = "EUR"):
    return SimpleNamespace(punti=punti, valuta=valuta)


def _scheda(**kw):
    base = {
        "tipo": "Obbligazione",
        "nome": "BTP Italia 2030",
        "valuta": "EUR",
        "descrizione": None,
        "mercato": None,
        "emittente": None,
        "scadenza": None,
        "cedola_annua": None,
        "struttura_bond": None,
        "tipologia": None,
        "frequenza_cedola": None,
        "settore": None,
        "ticker": None,
        "isin": None,
    }
    base.update(kw)
    return SimpleNamespace(**base)


def _cerca_result(isin, nome, tipo, link=None):
    # The site search carries the market routing params in the result link; a
    # non-fund result without a parseable mic is filtered out as a dead result.
    if link is None:
        link = f"https://www.borsaitaliana.it/borsa/search/scheda.html?code={isin}&mic=MTAA&lang=it"
    return SimpleNamespace(isin=isin, nome=nome, tipo=tipo, link=link)


# ── pure helpers ─────────────────────────────────────────────────────────────


def test_infer_country_from_issuer():
    assert bi._infer_country_from_issuer(None) is None
    assert bi._infer_country_from_issuer("") is None
    assert bi._infer_country_from_issuer("Republic of Italy") == "ITA"  # exact
    assert bi._infer_country_from_issuer("United States Of America") == "USA"  # exact, mixed case
    assert bi._infer_country_from_issuer("The Federal Republic of Germany, Berlin") == "DEU"  # substring
    assert bi._infer_country_from_issuer("Nowhere Land") is None


def test_infer_sector():
    assert bi._infer_sector(_scheda(settore="Technology")) == "Technology"  # stock
    assert bi._infer_sector(_scheda(settore=None, tipologia="Government Bonds")) == "Financials"  # bond map
    assert bi._infer_sector(_scheda(settore=None, tipologia="Something Unmapped")) is None
    assert bi._infer_sector(_scheda(settore=None, tipologia=None)) is None


def test_select_period_thresholds():
    today = date.today()

    def period(days):
        return bi._select_period(today - timedelta(days=days), today)

    assert period(10) == "1M"
    assert period(60) == "3M"
    assert period(120) == "6M"
    assert period(300) == "1Y"
    assert period(800) == "3Y"
    assert period(1500) == "5Y"
    assert period(3000) == "MAX"


def test_map_asset_type():
    assert bi._map_asset_type("Azione") == AssetType.STOCK
    assert bi._map_asset_type("bond") == AssetType.BOND
    assert bi._map_asset_type("ETF") == AssetType.ETF
    assert bi._map_asset_type("Fondi Comuni") == AssetType.FUND
    assert bi._map_asset_type("nonsense") is None
    assert bi._map_asset_type("") is None


def test_get_session_lazy_init(monkeypatch):
    """The real _get_session lazily builds and caches a single Sessione."""
    created = {"n": 0}

    class _DummySessione:
        def __init__(self):
            created["n"] += 1

    monkeypatch.setattr(bi, "Sessione", _DummySessione, raising=False)
    monkeypatch.setattr(bi, "_shared_session", None, raising=False)
    s1 = _REAL_GET_SESSION()
    s2 = _REAL_GET_SESSION()
    assert s1 is s2
    assert created["n"] == 1


# ── identity / availability / params ─────────────────────────────────────────


def test_identity_and_urls():
    p = _provider()
    assert p.provider_code == "borsa_italiana"
    assert p.provider_name == "Borsa Italiana"
    assert p.supports_meaningful_volume is True
    assert p.volume_kind == FAVolumeKind.TRADED_SHARES
    assert p.accepted_identifier_types == [ProviderInputType.ISIN]
    assert p.supports_history is True
    assert p.get_icon.startswith("https://")
    assert p.provider_help_url.startswith("/mkdocs/")
    assert p.resolvable_url_domains == ["borsaitaliana.it"]
    assert p.test_cases and p.test_search_query == "ENEL"
    assert [s["key"] for s in p.params_schema] == ["language", "codice_fondo", "mic", "platform"]
    # get_asset_url: ISIN scheda vs fund-by-code
    assert "scheda.html?code=IT0003128367" in p.get_asset_url("IT0003128367")
    fund_url = p.get_asset_url("IT0003128367", provider_params={"codice_fondo": "ABC123", "language": "it"})
    assert "fondi/dettaglio/ABC123.html" in fund_url and "lang=it" in fund_url
    # _get_lingua default + override
    assert p._get_lingua(None) == "en"
    assert p._get_lingua({"language": "it"}) == "it"


def test_get_asset_url_market_params():
    """mic/platform from provider_params route the scheda URL; absent → legacy bare URL."""
    p = _provider()
    url = p.get_asset_url("US912810TU25", IdentifierType.ISIN, {"language": "it", "mic": "ETLX", "platform": "TLX"})
    assert url == "https://www.borsaitaliana.it/borsa/search/scheda.html?code=US912810TU25&lang=it&mic=ETLX&platform=TLX"
    # mic without platform: only the mic segment is appended
    mic_only = p.get_asset_url("IT0005436693", IdentifierType.ISIN, {"language": "it", "mic": "MOTX"})
    assert mic_only == "https://www.borsaitaliana.it/borsa/search/scheda.html?code=IT0005436693&lang=it&mic=MOTX"
    # no market params → bare legacy URL (assets saved before mic/platform propagation)
    bare = p.get_asset_url("IT0003128367", IdentifierType.ISIN, {"language": "it"})
    assert bare == "https://www.borsaitaliana.it/borsa/search/scheda.html?code=IT0003128367&lang=it"
    # fund-by-code path unchanged
    fund_url = p.get_asset_url("LU2178929613", IdentifierType.ISIN, {"codice_fondo": "2FADB602822", "language": "it"})
    assert fund_url == "https://www.borsaitaliana.it/borsa/fondi/dettaglio/2FADB602822.html?lang=it"


@pytest.mark.asyncio
async def test_unavailable_library_raises(monkeypatch):
    monkeypatch.setattr(bi, "BORSA_ITALIANA_AVAILABLE", False)
    with pytest.raises(AssetSourceError) as exc:
        await _provider().get_current_value("IT0003128367", IdentifierType.ISIN)
    assert exc.value.error_code == "NOT_AVAILABLE"


def test_validate_params():
    p = _provider()
    p.validate_params(None)  # no-op
    p.validate_params({"language": "it"})  # supported
    with pytest.raises(AssetSourceError) as exc:
        p.validate_params({"language": "de"})
    assert exc.value.error_code == "INVALID_PARAMS"


# ── get_current_value ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_current_value_invalid_type():
    with pytest.raises(AssetSourceError) as exc:
        await _provider().get_current_value("X", IdentifierType.TICKER)
    assert exc.value.error_code == "INVALID_IDENTIFIER_TYPE"


@pytest.mark.asyncio
async def test_current_value_happy(monkeypatch):
    monkeypatch.setattr(bi, "ottieni_prezzo_corrente", lambda ident, sessione=None, mic=None, platform=None: _prezzo(Decimal("6.42"), "EUR", date(2026, 2, 11)), raising=False)
    result = await _provider().get_current_value("IT0003128367", IdentifierType.ISIN)
    assert result.value == Decimal("6.42")
    assert result.currency == "EUR"
    assert result.as_of_date == date(2026, 2, 11)
    assert result.source == "Borsa Italiana"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "exc_name,expected_code",
    [
        ("StrumentoNonTrovato", "NOT_FOUND"),
        ("DatiNonDisponibili", "NO_DATA"),
        ("BorsaItalianaErrore", "FETCH_ERROR"),
    ],
)
async def test_current_value_library_error_mapping(monkeypatch, exc_name, expected_code):
    exc_cls = getattr(bi, exc_name)

    def boom(ident, sessione=None, mic=None, platform=None):
        raise exc_cls("lib error")

    monkeypatch.setattr(bi, "ottieni_prezzo_corrente", boom, raising=False)
    with pytest.raises(AssetSourceError) as exc:
        await _provider().get_current_value("IT0003128367", IdentifierType.ISIN)
    assert exc.value.error_code == expected_code


@pytest.mark.asyncio
async def test_current_value_unexpected_error(monkeypatch):
    def boom(ident, sessione=None, mic=None, platform=None):
        raise ValueError("something odd")

    monkeypatch.setattr(bi, "ottieni_prezzo_corrente", boom, raising=False)
    with pytest.raises(AssetSourceError) as exc:
        await _provider().get_current_value("IT0003128367", IdentifierType.ISIN)
    assert exc.value.error_code == "FETCH_ERROR"


@pytest.mark.asyncio
async def test_current_value_unresolved_page_maps_to_unsupported(monkeypatch):
    """StrumentoNonRisolto (subclass of StrumentoNonTrovato) must map to the actionable
    UNSUPPORTED_PAGE, not to NOT_FOUND — the except order is the contract under test."""

    def boom(ident, sessione=None, mic=None, platform=None):
        raise StrumentoNonRisolto("no market page")

    monkeypatch.setattr(bi, "ottieni_prezzo_corrente", boom, raising=False)
    with pytest.raises(AssetSourceError) as exc:
        await _provider().get_current_value("US912810TU25", IdentifierType.ISIN, {"mic": "ETLX", "platform": "TLX"})
    assert exc.value.error_code == "UNSUPPORTED_PAGE"


# ── get_history_value ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_history_invalid_type():
    with pytest.raises(AssetSourceError) as exc:
        await _provider().get_history_value("X", IdentifierType.TICKER, None, date(2026, 1, 1), date(2026, 1, 31))
    assert exc.value.error_code == "INVALID_IDENTIFIER_TYPE"


@pytest.mark.asyncio
async def test_history_happy_with_filter_and_fallbacks(monkeypatch):
    today = date.today()
    start = today - timedelta(days=10)
    punti = [
        _punto(today - timedelta(days=5), apertura=Decimal("10"), massimo=Decimal("11"), minimo=Decimal("9"), chiusura=Decimal("10.5"), ultimo=Decimal("10.4"), volume=1000),
        # chiusura falsy → close falls back to ultimo; apertura/volume falsy → None
        _punto(today - timedelta(days=3), apertura=None, massimo=None, minimo=None, chiusura=None, ultimo=Decimal("12"), volume=0),
        _punto(today - timedelta(days=20), chiusura=Decimal("8"), ultimo=Decimal("8")),  # before range
        _punto(today + timedelta(days=2), chiusura=Decimal("13"), ultimo=Decimal("13")),  # after range
    ]
    monkeypatch.setattr(bi, "ottieni_storico", lambda ident, periodo=None, sessione=None: _storico(punti), raising=False)

    result = await _provider().get_history_value("IT0003128367", IdentifierType.ISIN, None, start, today)
    assert result.currency == "EUR"
    assert [p.date for p in result.prices] == [today - timedelta(days=5), today - timedelta(days=3)]
    p0, p1 = result.prices
    assert p0.close == Decimal("10.5") and p0.open == Decimal("10") and p0.volume == 1000
    assert p1.close == Decimal("12") and p1.open is None and p1.volume is None


@pytest.mark.asyncio
async def test_history_currency_from_library(monkeypatch):
    """History currency comes from the library result (EuroTLX hosts FX-denominated
    bonds), not from a hardcoded EUR."""
    today = date.today()
    punti = [
        _punto(today - timedelta(days=2), chiusura=Decimal("99"), ultimo=Decimal("99")),
        _punto(today - timedelta(days=1), chiusura=Decimal("100"), ultimo=Decimal("100")),
    ]
    monkeypatch.setattr(bi, "ottieni_storico", lambda ident, periodo=None, sessione=None: _storico(punti, valuta="USD"), raising=False)

    result = await _provider().get_history_value("US912810TU25", IdentifierType.ISIN, None, today - timedelta(days=5), today)
    assert result.currency == "USD"
    assert len(result.prices) == 2
    assert {p.currency for p in result.prices} == {"USD"}


@pytest.mark.asyncio
async def test_history_ohlc_guard_widens_fixing_outside_trade_range(monkeypatch):
    """EuroTLX reports the official daily fixing as `close` even when it falls outside
    the day's traded [low, high] (illiquid bonds). The base-class OHLC guard must widen
    the candle bounds around close instead of letting the core reject the point.

    Regression for the production failure: 'rejected N date(s) with impossible OHLC
    (close outside [low, high])' on US912810TU25 sync."""
    today = date.today()
    punti = [
        # close (fixing) ABOVE the traded high — the exact 2026-06-08 case
        _punto(today - timedelta(days=2), apertura=Decimal("92.87"), massimo=Decimal("92.87"), minimo=Decimal("92.87"), chiusura=Decimal("92.90"), ultimo=Decimal("92.87")),
        # close (fixing) BELOW the traded low
        _punto(today - timedelta(days=1), apertura=Decimal("93.59"), massimo=Decimal("93.59"), minimo=Decimal("92.92"), chiusura=Decimal("92.81"), ultimo=Decimal("92.92")),
        # an already-consistent candle must pass through untouched
        _punto(today, apertura=Decimal("93"), massimo=Decimal("94"), minimo=Decimal("92"), chiusura=Decimal("93.5"), ultimo=Decimal("93.5")),
    ]
    monkeypatch.setattr(bi, "ottieni_storico", lambda ident, periodo=None, sessione=None: _storico(punti, valuta="USD"), raising=False)

    result = await _provider().get_history_value("US912810TU25", IdentifierType.ISIN, None, today - timedelta(days=5), today)

    # No point may violate low <= close <= high after the guard
    for p in result.prices:
        if p.low is not None and p.high is not None:
            assert p.low <= p.close <= p.high, f"{p.date}: close={p.close} outside [{p.low},{p.high}]"
    r0, r1, r2 = result.prices
    # close (the fixing) is preserved verbatim; only the bounds widen
    assert r0.close == Decimal("92.90") and r0.high == Decimal("92.90") and r0.low == Decimal("92.87")
    assert r1.close == Decimal("92.81") and r1.low == Decimal("92.81") and r1.high == Decimal("93.59")
    # consistent candle untouched
    assert r2.open == Decimal("93") and r2.high == Decimal("94") and r2.low == Decimal("92") and r2.close == Decimal("93.5")


@pytest.mark.asyncio
async def test_history_unresolved_page_maps_to_unsupported(monkeypatch):
    """Same StrumentoNonRisolto → UNSUPPORTED_PAGE mapping as get_current_value."""

    def boom(ident, periodo=None, sessione=None):
        raise StrumentoNonRisolto("no market page")

    monkeypatch.setattr(bi, "ottieni_storico", boom, raising=False)
    with pytest.raises(AssetSourceError) as exc:
        await _provider().get_history_value("US912810TU25", IdentifierType.ISIN, None, date(2026, 1, 1), date(2026, 1, 31))
    assert exc.value.error_code == "UNSUPPORTED_PAGE"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "exc_name,expected_code",
    [
        ("StrumentoNonTrovato", "NOT_FOUND"),
        ("DatiNonDisponibili", "NO_DATA"),
        ("BorsaItalianaErrore", "FETCH_ERROR"),
    ],
)
async def test_history_library_error_mapping(monkeypatch, exc_name, expected_code):
    exc_cls = getattr(bi, exc_name)

    def boom(ident, periodo=None, sessione=None):
        raise exc_cls("lib error")

    monkeypatch.setattr(bi, "ottieni_storico", boom, raising=False)
    with pytest.raises(AssetSourceError) as exc:
        await _provider().get_history_value("IT0003128367", IdentifierType.ISIN, None, date(2026, 1, 1), date(2026, 1, 31))
    assert exc.value.error_code == expected_code


@pytest.mark.asyncio
async def test_history_unexpected_error(monkeypatch):
    def boom(ident, periodo=None, sessione=None):
        raise ValueError("odd")

    monkeypatch.setattr(bi, "ottieni_storico", boom, raising=False)
    with pytest.raises(AssetSourceError) as exc:
        await _provider().get_history_value("IT0003128367", IdentifierType.ISIN, None, "min", date(2026, 1, 31))
    assert exc.value.error_code == "FETCH_ERROR"


# ── _fetch_fund error mappings (via fund current value) ──────────────────────


@pytest.mark.asyncio
async def test_fund_current_value_no_data(monkeypatch):
    def boom(codice, sessione=None):
        raise bi.DatiNonDisponibili("no nav")

    monkeypatch.setattr(bi, "ottieni_dati_fondo", boom, raising=False)
    with pytest.raises(AssetSourceError) as exc:
        await _provider().get_current_value("LU123", IdentifierType.ISIN, {"codice_fondo": "ABC"})
    assert exc.value.error_code == "NO_DATA"


@pytest.mark.asyncio
async def test_fund_current_value_fetch_error(monkeypatch):
    def boom(codice, sessione=None):
        raise bi.BorsaItalianaErrore("boom")

    monkeypatch.setattr(bi, "ottieni_dati_fondo", boom, raising=False)
    with pytest.raises(AssetSourceError) as exc:
        await _provider().get_current_value("LU123", IdentifierType.ISIN, {"codice_fondo": "ABC"})
    assert exc.value.error_code == "FETCH_ERROR"


# ── fetch_asset_metadata (ISIN scheda path) ──────────────────────────────────


@pytest.mark.asyncio
async def test_metadata_non_isin_returns_none():
    result = await _provider().fetch_asset_metadata("X", IdentifierType.TICKER)
    assert result is None


@pytest.mark.asyncio
async def test_metadata_scheda_bond_full(monkeypatch):
    scheda = _scheda(
        tipo="Obbligazione",
        nome="BTP 2030",
        valuta="EUR",
        descrizione="Buono del Tesoro Poliennale",
        mercato="MOT",
        emittente="Republic of Italy",
        scadenza=date(2030, 3, 1),
        cedola_annua=Decimal("2.5"),
        struttura_bond="Fixed rate",
        tipologia="Government Bonds",
        frequenza_cedola="Semi-annual",
        settore=None,
        ticker="BTP30",
        isin="IT0005436693",
    )
    monkeypatch.setattr(bi, "ottieni_scheda", lambda ident, mic=None, lingua=None, sessione=None, platform=None, url_diretto=None: scheda, raising=False)

    result = await _provider().fetch_asset_metadata("IT0005436693", IdentifierType.ISIN, {"language": "it"})
    assert result is not None
    assert result.asset_type == AssetType.BOND
    assert result.currency == "EUR"
    assert result.identifier_isin == "IT0005436693"
    assert result.identifier_ticker == "BTP30"
    sd = result.classification_params.short_description
    assert "Market: MOT" in sd and "Issuer: Republic of Italy" in sd
    assert "Maturity: 2030-03-01" in sd and "Annual coupon: 2.5%" in sd
    assert "Structure: Fixed rate" in sd and "Coupon frequency: Semi-annual" in sd
    # issuer → geographic area (ITA), tipologia → sector (Financials)
    assert result.classification_params.geographic_area is not None
    assert result.classification_params.sector_area is not None


@pytest.mark.asyncio
async def test_metadata_scheda_long_description_truncated(monkeypatch):
    scheda = _scheda(descrizione="D" * 600, isin="IT0005436693", ticker=None)
    monkeypatch.setattr(bi, "ottieni_scheda", lambda ident, mic=None, lingua=None, sessione=None, platform=None, url_diretto=None: scheda, raising=False)
    result = await _provider().fetch_asset_metadata("IT0005436693", IdentifierType.ISIN)
    sd = result.classification_params.short_description
    assert len(sd) == 500 and sd.endswith("...")
    assert result.identifier_ticker is None


@pytest.mark.asyncio
async def test_metadata_scheda_exception_returns_none(monkeypatch):
    def boom(ident, mic=None, lingua=None, sessione=None, platform=None):
        raise RuntimeError("scheda parse error")

    monkeypatch.setattr(bi, "ottieni_scheda", boom, raising=False)
    assert await _provider().fetch_asset_metadata("IT0005436693", IdentifierType.ISIN) is None


@pytest.mark.asyncio
async def test_metadata_scheda_unresolved_page_raises_unsupported(monkeypatch):
    """An unresolvable market page is actionable: surfaced as UNSUPPORTED_PAGE,
    not swallowed into a None like ordinary parse failures."""

    def boom(ident, mic=None, lingua=None, sessione=None, platform=None):
        raise StrumentoNonRisolto("no market page")

    monkeypatch.setattr(bi, "ottieni_scheda", boom, raising=False)
    with pytest.raises(AssetSourceError) as exc:
        await _provider().fetch_asset_metadata("US912810TU25", IdentifierType.ISIN, {"mic": "ETLX", "platform": "TLX"})
    assert exc.value.error_code == "UNSUPPORTED_PAGE"


@pytest.mark.asyncio
async def test_metadata_scheda_minimal_no_optional_fields(monkeypatch):
    # tipo/nome/valuta only — every optional description field is None, so the
    # description stays None and no geographic/sector area is built.
    scheda = _scheda(tipo="Azione", nome="ENEL", valuta="EUR", isin="IT0003128367")
    monkeypatch.setattr(bi, "ottieni_scheda", lambda ident, mic=None, lingua=None, sessione=None, platform=None, url_diretto=None: scheda, raising=False)
    result = await _provider().fetch_asset_metadata("IT0003128367", IdentifierType.ISIN)
    assert result.asset_type == AssetType.STOCK
    assert result.classification_params.short_description is None
    assert result.classification_params.geographic_area is None
    assert result.classification_params.sector_area is None


# ── fund metadata (by internal code) ─────────────────────────────────────────


def _fund_ns(**kw):
    base = {
        "codice": "ABC123",
        "nome": "Eurizon PIR Italia",
        "isin": "IT0001111111",
        "valuta": "EUR",
        "nav": Decimal("100.0"),
        "data_nav": date.today(),
        "caratteristiche": {"Categoria": "Azionario Italia"},
        "societa_gestione": {"Gestore": "Eurizon"},
        "costi": {"TER": "1.20%"},
    }
    base.update(kw)
    return SimpleNamespace(**base)


@pytest.mark.asyncio
async def test_fund_metadata_happy(monkeypatch):
    monkeypatch.setattr(bi, "ottieni_dati_fondo", lambda codice, sessione=None: _fund_ns(), raising=False)
    result = await _provider().fetch_asset_metadata("IT0001111111", IdentifierType.ISIN, {"codice_fondo": "ABC123", "language": "it"})
    assert result is not None
    assert result.asset_type == AssetType.FUND
    assert result.currency == "EUR"
    assert result.identifier_isin == "IT0001111111"
    assert result.identifier_other == ["ABC123"]
    sd = result.classification_params.short_description
    assert "ISIN: IT0001111111" in sd
    assert "Categoria: Azionario Italia" in sd
    assert "Società di Gestione — Gestore: Eurizon" in sd
    assert "Costi — TER: 1.20%" in sd


@pytest.mark.asyncio
async def test_fund_metadata_long_description_truncated(monkeypatch):
    monkeypatch.setattr(bi, "ottieni_dati_fondo", lambda codice, sessione=None: _fund_ns(costi={"Note": "x" * 600}), raising=False)
    result = await _provider().fetch_asset_metadata("IT0001111111", IdentifierType.ISIN, {"codice_fondo": "ABC123"})
    sd = result.classification_params.short_description
    assert len(sd) == 500 and sd.endswith("...")


@pytest.mark.asyncio
async def test_fund_metadata_fetch_fails_returns_none(monkeypatch):
    def boom(codice, sessione=None):
        raise bi.BorsaItalianaErrore("page down")

    monkeypatch.setattr(bi, "ottieni_dati_fondo", boom, raising=False)
    result = await _provider().fetch_asset_metadata("IT0001111111", IdentifierType.ISIN, {"codice_fondo": "ABC123"})
    assert result is None


def test_build_fund_description_missing_name_and_isin():
    p = _provider()
    # nome + isin both falsy → only the section entries survive.
    ns = SimpleNamespace(nome=None, isin=None, caratteristiche={"Categoria": "X"}, societa_gestione=None, costi=None)
    assert p._build_fund_description(ns) == "Categoria: X"
    # nothing at all → None.
    empty = SimpleNamespace(nome=None, isin=None, caratteristiche=None, societa_gestione=None, costi=None)
    assert p._build_fund_description(empty) is None


# ── search error / dedup / general-item paths ────────────────────────────────


@pytest.mark.asyncio
async def test_search_dedup_and_stock_items(monkeypatch):
    results = [
        _cerca_result("IT0003128367", "ENEL", "Azione"),
        _cerca_result("IT0003128367", "ENEL dup", "Azione"),  # duplicate ISIN → skipped
    ]
    monkeypatch.setattr(bi, "cerca", lambda q, lingua=None, sessione=None: results, raising=False)

    items = await _provider().search("ENEL")
    # one instrument, two language rows (it, en)
    assert len(items) == 2
    assert {it["identifier"] for it in items} == {"IT0003128367"}
    assert {it["type"] for it in items} == {AssetType.STOCK.value}
    langs = {it["provider_params"]["language"] for it in items}
    assert langs == {"it", "en"}
    # currency is not in the search payload — left unknown, metadata fills it
    assert {it["currency"] for it in items} == {None}
    # market routing params are parsed from the site link into provider_params
    assert {it["provider_params"]["mic"] for it in items} == {"MTAA"}


@pytest.mark.asyncio
async def test_search_service_unavailable(monkeypatch):
    def boom(q, lingua=None, sessione=None):
        raise bi.RicercaNonDisponibile("search down")

    monkeypatch.setattr(bi, "cerca", boom, raising=False)
    with pytest.raises(AssetSourceError) as exc:
        await _provider().search("ENEL")
    assert exc.value.error_code == "FETCH_ERROR"


@pytest.mark.asyncio
async def test_search_generic_error(monkeypatch):
    def boom(q, lingua=None, sessione=None):
        raise ValueError("odd")

    monkeypatch.setattr(bi, "cerca", boom, raising=False)
    with pytest.raises(AssetSourceError) as exc:
        await _provider().search("ENEL")
    assert exc.value.error_code == "SEARCH_ERROR"


# ── resolve_url error branches ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_resolve_url_non_borsa_returns_none():
    assert await _provider().resolve_url("https://example.com/foo") is None
    assert await _provider().resolve_url("") is None


@pytest.mark.asyncio
async def test_resolve_url_fund_page_errors_return_none(monkeypatch):
    monkeypatch.setattr(bi, "estrai_codice_da_url", lambda url: "ABC123", raising=False)

    def not_found(url, sessione=None):
        raise bi.StrumentoNonTrovato("gone")

    monkeypatch.setattr(bi, "ottieni_dati_fondo_da_url", not_found, raising=False)
    assert await _provider().resolve_url("https://www.borsaitaliana.it/borsa/fondi/dettaglio/ABC123.html") is None

    def generic(url, sessione=None):
        raise RuntimeError("boom")

    monkeypatch.setattr(bi, "ottieni_dati_fondo_da_url", generic, raising=False)
    assert await _provider().resolve_url("https://www.borsaitaliana.it/borsa/fondi/dettaglio/ABC123.html") is None


@pytest.mark.asyncio
async def test_resolve_url_scheda_page(monkeypatch):
    monkeypatch.setattr(bi, "estrai_codice_da_url", lambda url: None, raising=False)  # not a fund
    scheda = _scheda(tipo="Azione", nome="ENEL", valuta="EUR", isin="IT0003128367")
    monkeypatch.setattr(bi, "ottieni_scheda", lambda ident, mic=None, lingua=None, sessione=None, platform=None, url_diretto=None: scheda, raising=False)
    # resolve_url rediscovers the authoritative mic/platform via the site search:
    # exact-ISIN hit whose link carries the market routing params.
    monkeypatch.setattr(bi, "cerca", lambda q, lingua=None, sessione=None: [_cerca_result("IT0003128367", "ENEL", "Azione")], raising=False)

    url = "https://www.borsaitaliana.it/borsa/azioni/scheda/IT0003128367.html"
    items = await _provider().resolve_url(url)
    assert items is not None and len(items) == 2
    assert {it["identifier"] for it in items} == {"IT0003128367"}
    assert {it["type"] for it in items} == {AssetType.STOCK.value}
    # the rediscovered mic lands in provider_params so the saved asset can be routed
    assert {it["provider_params"]["mic"] for it in items} == {"MTAA"}


@pytest.mark.asyncio
async def test_resolve_url_scheda_errors_return_none(monkeypatch):
    monkeypatch.setattr(bi, "estrai_codice_da_url", lambda url: None, raising=False)
    # No site-search rediscovery here: empty result → URL-only mic fallback.
    monkeypatch.setattr(bi, "cerca", lambda q, lingua=None, sessione=None: [], raising=False)
    url = "https://www.borsaitaliana.it/borsa/azioni/scheda/IT0003128367.html"

    def not_found(ident, mic=None, lingua=None, sessione=None, platform=None):
        raise bi.DatiNonDisponibili("no scheda")

    monkeypatch.setattr(bi, "ottieni_scheda", not_found, raising=False)
    assert await _provider().resolve_url(url) is None

    def generic(ident, mic=None, lingua=None, sessione=None, platform=None):
        raise RuntimeError("boom")

    monkeypatch.setattr(bi, "ottieni_scheda", generic, raising=False)
    assert await _provider().resolve_url(url) is None


@pytest.mark.asyncio
async def test_resolve_url_unmatched_borsa_url_returns_none(monkeypatch):
    monkeypatch.setattr(bi, "estrai_codice_da_url", lambda url: None, raising=False)
    # A borsaitaliana.it URL that is neither a fund code nor a scheda ISIN pattern.
    assert await _provider().resolve_url("https://www.borsaitaliana.it/borsa/homepage.html") is None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
