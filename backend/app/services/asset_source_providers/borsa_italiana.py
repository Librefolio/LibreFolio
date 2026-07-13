"""
Borsa Italiana provider for asset pricing.

Uses the borsa-italiana-scraping library to fetch financial data
from borsaitaliana.it (stocks, bonds, ETFs listed on Borsa Italiana).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Dict, List

from backend.app.db import IdentifierType
from backend.app.db.models import AssetType, ProviderInputType
from backend.app.logging_config import get_logger
from backend.app.schemas.assets import (
    FAAssetPatchItem,
    FAClassificationParams,
    FACurrentValue,
    FAGeographicArea,
    FAHistoricalData,
    FAPricePoint,
    FASectorArea,
)
from backend.app.services.asset_source import ASSET_HISTORY_MIN_FALLBACK, AssetHistoryStartDate, AssetSourceError, AssetSourceProvider
from backend.app.services.provider_registry import AssetProviderRegistry, register_provider

try:
    from borsa_italiana_scraping import (
        BorsaItalianaErrore,
        DatiNonDisponibili,
        RicercaNonDisponibile,
        Sessione,
        StrumentoNonTrovato,
        cerca,
        ottieni_prezzo_corrente,
        ottieni_scheda,
        ottieni_storico,
    )

    BORSA_ITALIANA_AVAILABLE = True
except ImportError:
    BORSA_ITALIANA_AVAILABLE = False

logger = get_logger(__name__)

# Shared session instance — reused across calls, closed on shutdown
_shared_session: Sessione | None = None


def _get_session() -> Sessione:
    """Get or create the shared HTTP session."""
    global _shared_session
    if _shared_session is None:
        _shared_session = Sessione()
    return _shared_session


# Map Borsa Italiana instrument type strings to AssetType enum.
# Keys are lowercase — lookup is case-insensitive via _map_asset_type().
_TIPO_TO_ASSET_TYPE: dict[str, AssetType] = {
    # Italian labels (lingua="it")
    "azione": AssetType.STOCK,
    "obbligazione": AssetType.BOND,
    "etf": AssetType.ETF,
    "etc/etn": AssetType.ETF,
    # English labels (lingua="en")
    "stock": AssetType.STOCK,
    "share": AssetType.STOCK,
    "bond": AssetType.BOND,
    "government bond": AssetType.BOND,
    "corporate bond": AssetType.BOND,
}


def _map_asset_type(tipo: str) -> AssetType | None:
    """Map a Borsa Italiana type string to AssetType (case-insensitive)."""
    return _TIPO_TO_ASSET_TYPE.get(tipo.lower().strip()) if tipo else None


# Issuer name → ISO-3166-A3 country code.
# Expandable: add new issuers as they appear.
_ISSUER_TO_COUNTRY: dict[str, str] = {
    "republic of italy": "ITA",
    "repubblica italiana": "ITA",
    "federal republic of germany": "DEU",
    "republic of france": "FRA",
    "republique francaise": "FRA",
    "kingdom of spain": "ESP",
    "republic of austria": "AUT",
    "kingdom of the netherlands": "NLD",
    "republic of portugal": "PRT",
    "republic of greece": "GRC",
    "republic of ireland": "IRL",
    "kingdom of belgium": "BEL",
    "republic of finland": "FIN",
    "united states of america": "USA",
    "united kingdom": "GBR",
}


def _infer_country_from_issuer(issuer: str | None) -> str | None:
    """Try to map issuer name to ISO-3166-A3 country code."""
    if not issuer:
        return None
    key = issuer.strip().lower()
    # Exact match first
    if key in _ISSUER_TO_COUNTRY:
        return _ISSUER_TO_COUNTRY[key]
    # Substring match (e.g. "Republic of Italy" inside longer string)
    for pattern, code in _ISSUER_TO_COUNTRY.items():
        if pattern in key:
            return code
    return None


# Bond tipologia → FinancialSector mapping.
# FASectorArea normalizes via FinancialSector.from_string().
# Keys in both EN and IT (case-insensitive lookup).
_TIPOLOGIA_TO_SECTOR: dict[str, str] = {
    # English
    "italian government bonds": "Financials",
    "government bonds": "Financials",
    "corporate": "Financials",
    "corporate bonds": "Financials",
    "supranational bonds": "Financials",
    # Italian
    "titoli di stato italiani": "Financials",
    "titoli di stato": "Financials",
    "obbligazioni corporate": "Financials",
    "obbligazioni sovranazionali": "Financials",
}


def _infer_sector(scheda) -> str | None:
    """Infer sector from scheda fields.

    Priority: scheda.settore (stocks) > scheda.tipologia (bonds).
    """
    # Stocks: direct sector field
    if scheda.settore:
        return scheda.settore
    # Bonds: map tipologia
    if scheda.tipologia:
        key = scheda.tipologia.strip().lower()
        return _TIPOLOGIA_TO_SECTOR.get(key)
    return None


def _select_period(start_date: date, end_date: date) -> str:
    """Select the best API period to cover the requested date range.

    The Borsa Italiana API returns data for the last N months/years relative
    to *today* (e.g. "1Y" = last 365 days from now). We pick the smallest
    period whose window reaches back to start_date.
    """
    days_back = (date.today() - start_date).days
    if days_back <= 30:
        return "1M"
    if days_back <= 90:
        return "3M"
    if days_back <= 180:
        return "6M"
    if days_back <= 365:
        return "1Y"
    if days_back <= 1095:
        return "3Y"
    if days_back <= 1825:
        return "5Y"
    return "MAX"


@register_provider(AssetProviderRegistry)
class BorsaItalianaProvider(AssetSourceProvider):
    """Borsa Italiana data provider using the borsa-italiana-scraping library.

    Supports stocks, bonds, and ETFs listed on Borsa Italiana (MTA, MOT, ETFPlus).
    Identifier type: ISIN.
    """

    def _check_availability(self):
        """Raise AssetSourceError if the library is not installed."""
        if not BORSA_ITALIANA_AVAILABLE:
            raise AssetSourceError(
                "borsa-italiana-scraping library not available — install with: " "pipenv install 'borsa-italiana-scraping @ git+https://github.com/Librefolio/borsaItaliana-scraping.git'",
                "NOT_AVAILABLE",
            )

    SUPPORTED_LANGUAGES = ("en", "it")
    LANGUAGE_FLAGS = {"en": "🇬🇧", "it": "🇮🇹"}

    def _get_lingua(self, provider_params: Dict | None) -> str:
        """Extract language from provider_params, default 'en'."""
        if provider_params and provider_params.get("language"):
            return provider_params["language"]
        return "en"

    # ── Properties ──────────────────────────────────────────────────────

    @property
    def provider_code(self) -> str:
        return "borsa_italiana"

    @property
    def provider_name(self) -> str:
        return "Borsa Italiana"

    @property
    def accepted_identifier_types(self) -> list:
        return [ProviderInputType.ISIN]

    @property
    def get_icon(self) -> str:
        """Return provider icon URL."""
        return "https://www.borsaitaliana.it/media-rwd/assets/images/favicon.ico"

    @property
    def provider_help_url(self) -> str:
        return "/mkdocs/developer/backend/assets/provider_borsa_italiana/"

    def get_asset_url(self, identifier, identifier_type=None, provider_params=None) -> str | None:
        """Generate URL to Borsa Italiana instrument page."""
        lingua = self._get_lingua(provider_params)
        return f"https://www.borsaitaliana.it/borsa/search/scheda.html?code={identifier}&lang={lingua}"

    @property
    def test_cases(self) -> list[dict]:
        return [
            {
                "identifier": "IT0003128367",  # ENEL S.p.A.
                "identifier_type": IdentifierType.ISIN,
                "provider_params": None,
            },
        ]

    @property
    def test_search_query(self) -> str | None:
        return "ENEL"

    @property
    def params_schema(self) -> list[dict]:
        return [
            {
                "key": "language",
                "type": "select",
                "required": False,
                "options": list(self.SUPPORTED_LANGUAGES),
                "option_labels": {"en": "🇬🇧 English", "it": "🇮🇹 Italiano"},
                "default": "en",
                "description": "Language for asset names and metadata.",
            }
        ]

    # ── Current value ───────────────────────────────────────────────────

    async def get_current_value(
        self,
        identifier: str,
        identifier_type: IdentifierType,
        provider_params: Dict | None = None,
    ) -> FACurrentValue:
        """Fetch current price from Borsa Italiana."""
        self._check_availability()
        if identifier_type != IdentifierType.ISIN:
            raise AssetSourceError(
                f"Borsa Italiana provider only supports ISIN, got {identifier_type}",
                "INVALID_IDENTIFIER_TYPE",
            )

        try:
            prezzo = ottieni_prezzo_corrente(identifier, sessione=_get_session())
            return FACurrentValue(
                value=prezzo.prezzo,
                currency=prezzo.valuta,
                as_of_date=prezzo.data,
                source=self.provider_name,
            )
        except StrumentoNonTrovato as e:
            raise AssetSourceError(
                f"Instrument not found on Borsa Italiana: {identifier}",
                "NOT_FOUND",
                {"identifier": identifier, "error": str(e)},
            ) from e
        except DatiNonDisponibili as e:
            raise AssetSourceError(
                f"No data available for {identifier} on Borsa Italiana",
                "NO_DATA",
                {"identifier": identifier, "error": str(e)},
            ) from e
        except BorsaItalianaErrore as e:
            raise AssetSourceError(
                f"Failed to fetch current value for {identifier} from Borsa Italiana: {e}",
                "FETCH_ERROR",
                {"identifier": identifier, "error": str(e)},
            ) from e
        except Exception as e:
            raise AssetSourceError(
                f"Unexpected error fetching current value for {identifier}: {e}",
                "FETCH_ERROR",
                {"identifier": identifier, "error": str(e)},
            ) from e

    # ── Historical data ─────────────────────────────────────────────────

    @property
    def supports_history(self) -> bool:
        return True

    async def get_history_value(
        self,
        identifier: str,
        identifier_type: IdentifierType,
        provider_params: Dict | None,
        start_date: AssetHistoryStartDate,
        end_date: date,
    ) -> FAHistoricalData:
        """Fetch historical OHLCV data from Borsa Italiana."""
        self._check_availability()
        if identifier_type != IdentifierType.ISIN:
            raise AssetSourceError(
                f"Borsa Italiana provider only supports ISIN, got {identifier_type}",
                "INVALID_IDENTIFIER_TYPE",
            )

        try:
            effective_start = ASSET_HISTORY_MIN_FALLBACK if start_date == "min" else start_date
            periodo = _select_period(effective_start, end_date)
            risultato = ottieni_storico(
                identifier,
                periodo=periodo,
                sessione=_get_session(),
            )

            prices: List[FAPricePoint] = []
            for punto in risultato.punti:
                # Filter to requested date range
                if punto.data < effective_start or punto.data > end_date:
                    continue
                prices.append(
                    FAPricePoint(
                        date=punto.data,
                        open=punto.apertura if punto.apertura else None,
                        high=punto.massimo if punto.massimo else None,
                        low=punto.minimo if punto.minimo else None,
                        close=punto.chiusura if punto.chiusura else punto.ultimo,
                        volume=punto.volume if punto.volume else None,
                        currency="EUR",
                        backward_fill_info=None,
                    )
                )

            return FAHistoricalData(
                prices=prices,
                currency="EUR",
                source=self.provider_name,
            )
        except StrumentoNonTrovato as e:
            raise AssetSourceError(
                f"Instrument not found on Borsa Italiana: {identifier}",
                "NOT_FOUND",
                {"identifier": identifier, "error": str(e)},
            ) from e
        except DatiNonDisponibili as e:
            raise AssetSourceError(
                f"No historical data for {identifier} on Borsa Italiana",
                "NO_DATA",
                {"identifier": identifier, "error": str(e)},
            ) from e
        except BorsaItalianaErrore as e:
            raise AssetSourceError(
                f"Failed to fetch history for {identifier} from Borsa Italiana: {e}",
                "FETCH_ERROR",
                {"identifier": identifier, "error": str(e)},
            ) from e
        except Exception as e:
            raise AssetSourceError(
                f"Unexpected error fetching history for {identifier}: {e}",
                "FETCH_ERROR",
                {"identifier": identifier, "error": str(e)},
            ) from e

    # ── Search ──────────────────────────────────────────────────────────

    async def search(self, query: str) -> list[dict]:
        """Search for instruments on Borsa Italiana.

        Emits 2 results per match (EN + IT) with flag emojis,
        similar to JustETF's multi-currency approach.
        """
        self._check_availability()
        try:
            # Fetch results in both languages in parallel-ish (sync lib, sequential)
            results_by_lang: dict[str, list] = {}
            for lingua in self.SUPPORTED_LANGUAGES:
                results_by_lang[lingua] = cerca(query, lingua=lingua, sessione=_get_session())

            items = []
            seen_pairs: set[tuple[str, str]] = set()  # (isin, lingua) dedup

            # Use EN results as primary (usually same ISINs), then fill from IT
            for lingua in self.SUPPORTED_LANGUAGES:
                flag = self.LANGUAGE_FLAGS[lingua]
                for r in results_by_lang[lingua]:
                    pair = (r.isin, lingua)
                    if pair in seen_pairs:
                        continue
                    seen_pairs.add(pair)
                    asset_type = _map_asset_type(r.tipo)
                    items.append(
                        {
                            "identifier": r.isin,
                            "identifier_type": IdentifierType.ISIN,
                            "display_name": f"{r.nome} {flag}",
                            "currency": "EUR",
                            "type": asset_type.value if asset_type else r.tipo,
                            "provider_params": {"language": lingua},
                        }
                    )
            return items
        except RicercaNonDisponibile as e:
            raise AssetSourceError(
                f"Search service unavailable on Borsa Italiana: {e}",
                "FETCH_ERROR",
                {"query": query, "error": str(e)},
            ) from e
        except Exception as e:
            raise AssetSourceError(
                f"Search failed for '{query}' on Borsa Italiana: {e}",
                "SEARCH_ERROR",
                {"query": query, "error": str(e)},
            ) from e

    # ── Metadata ────────────────────────────────────────────────────────

    async def fetch_asset_metadata(
        self,
        identifier: str,
        identifier_type: IdentifierType,
        provider_params: Dict | None = None,
    ) -> FAAssetPatchItem | None:
        """Fetch asset metadata from Borsa Italiana instrument page."""
        self._check_availability()
        if identifier_type != IdentifierType.ISIN:
            return None

        try:
            lingua = self._get_lingua(provider_params)
            scheda = ottieni_scheda(identifier, lingua=lingua, sessione=_get_session())

            asset_type = _map_asset_type(scheda.tipo)

            # Build description
            description_parts = []
            if scheda.descrizione:
                description_parts.append(scheda.descrizione)
            if scheda.mercato:
                description_parts.append(f"Market: {scheda.mercato}")
            if scheda.emittente:
                description_parts.append(f"Issuer: {scheda.emittente}")
            if scheda.scadenza:
                description_parts.append(f"Maturity: {scheda.scadenza.isoformat()}")
            if scheda.cedola_annua is not None:
                description_parts.append(f"Annual coupon: {scheda.cedola_annua}%")

            if scheda.struttura_bond:
                description_parts.append(f"Structure: {scheda.struttura_bond}")
            if scheda.tipologia:
                description_parts.append(f"Tipology: {scheda.tipologia}")
            if scheda.frequenza_cedola:
                description_parts.append(f"Coupon frequency: {scheda.frequenza_cedola}")

            short_description = " | ".join(description_parts) if description_parts else None
            if short_description and len(short_description) > 500:
                short_description = short_description[:497] + "..."

            # Geographic area from issuer
            geographic_area = None
            country_code = _infer_country_from_issuer(scheda.emittente)
            if country_code:
                try:
                    geographic_area = FAGeographicArea(distribution={country_code: Decimal("1.0")})
                except Exception as e:
                    logger.debug(f"Could not create FAGeographicArea for {identifier}: {e}")

            # Sector from settore (stocks) or tipologia (bonds)
            sector_area = None
            sector_name = _infer_sector(scheda)
            if sector_name:
                try:
                    sector_area = FASectorArea(distribution={sector_name: Decimal("1.0")})
                except Exception as e:
                    logger.debug(f"Could not create FASectorArea for {identifier}: {e}")

            classification = FAClassificationParams(
                short_description=short_description,
                geographic_area=geographic_area,
                sector_area=sector_area,
            )

            return FAAssetPatchItem(
                asset_id=0,  # Placeholder — caller sets the real ID
                display_name=f"{scheda.nome} {self.LANGUAGE_FLAGS[lingua]}",
                currency=scheda.valuta,
                asset_type=asset_type,
                classification_params=classification,
                identifier_isin=identifier,
                identifier_ticker=scheda.ticker if scheda.ticker else None,
            )
        except Exception as e:
            logger.warning(f"Could not fetch metadata for {identifier} from Borsa Italiana: {e}")
            return None

    # ── Params ──────────────────────────────────────────────────────────

    def validate_params(self, params: Dict | None) -> None:
        """Validate provider_params: language must be 'en' or 'it'."""
        if not params:
            return
        language = params.get("language")
        if language and language not in self.SUPPORTED_LANGUAGES:
            raise AssetSourceError(
                f"Unsupported language '{language}'. Must be one of: {', '.join(self.SUPPORTED_LANGUAGES)}",
                "INVALID_PARAMS",
                {"language": language, "supported": list(self.SUPPORTED_LANGUAGES)},
            )

    # ── Shutdown ─────────────────────────────────────────────────────────

    def shutdown(self) -> None:  # pragma: no cover
        """Close the shared HTTP session."""
        global _shared_session
        if _shared_session is not None:
            _shared_session.chiudi()
            _shared_session = None
            logger.debug("Borsa Italiana shared session closed")
