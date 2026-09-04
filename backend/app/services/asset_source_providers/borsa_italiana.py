"""
Borsa Italiana provider for asset pricing.

Uses the borsa-italiana-scraping library to fetch financial data
from borsaitaliana.it (stocks, bonds, ETFs listed on Borsa Italiana).
"""

from __future__ import annotations

import re
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
from backend.app.schemas.provider import FAVolumeKind
from backend.app.services.asset_source import ASSET_HISTORY_MIN_FALLBACK, AssetHistoryStartDate, AssetSourceError, AssetSourceProvider
from backend.app.services.provider_registry import AssetProviderRegistry, register_provider

try:
    from borsa_italiana_scraping import (
        BorsaItalianaErrore,
        DatiFondo,
        DatiNonDisponibili,
        RicercaNonDisponibile,
        Sessione,
        StrumentoNonTrovato,
        cerca,
        estrai_codice_da_url,
        ottieni_dati_fondo,
        ottieni_dati_fondo_da_url,
        ottieni_prezzo_corrente,
        ottieni_scheda,
        ottieni_storico,
    )

    BORSA_ITALIANA_AVAILABLE = True
except ImportError:
    BORSA_ITALIANA_AVAILABLE = False

logger = get_logger(__name__)

# ISIN (optionally followed by a ``-MIC`` market segment) embedded in a Borsa
# Italiana stock/bond/ETF scheda URL, e.g. ``…/scheda/IT0005436693-MOTX.html``.
# Used by ``resolve_url`` to turn a web link-finder hit into a search item for
# instruments the on-site search can't match by descriptive name.
_SCHEDA_ISIN_RE = re.compile(r"/([A-Z]{2}[A-Z0-9]{9}[0-9])(?:-([A-Za-z0-9]+))?\.html")

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
    "fondi comuni": AssetType.FUND,
    # English labels (lingua="en")
    "stock": AssetType.STOCK,
    "share": AssetType.STOCK,
    "bond": AssetType.BOND,
    "government bond": AssetType.BOND,
    "corporate bond": AssetType.BOND,
    "fund": AssetType.FUND,
    "common fund": AssetType.FUND,
    "common funds": AssetType.FUND,
}


def _map_asset_type(tipo: str) -> AssetType | None:
    """Map a Borsa Italiana type string to AssetType (case-insensitive)."""
    return _TIPO_TO_ASSET_TYPE.get(tipo.lower().strip()) if tipo else None


_SEARCH_TERM_ABBREVIATIONS: tuple[tuple[str, str], ...] = (
    ("obbligazionaria", "obbligaz"),
    ("obbligazionario", "obbligaz"),
    ("azionaria", "azion"),
    ("azionario", "azion"),
    ("conservativa", "conserv"),
    ("conservativo", "conserv"),
    ("dinamica", "din"),
    ("dinamico", "din"),
)


def _search_query_variants(query: str) -> list[str]:
    """Return Borsa search variants for fund titles indexed with abbreviations."""
    normalized = re.sub(r"\s+", " ", query.replace("-", " ")).strip()
    variants: list[str] = []
    seen: set[str] = set()

    def add_variant(value: str) -> None:
        value = re.sub(r"\s+", " ", value).strip()
        key = value.lower()
        if value and key not in seen:
            seen.add(key)
            variants.append(value)

    add_variant(query)
    add_variant(normalized)

    abbreviated = normalized
    for full_term, abbreviation in _SEARCH_TERM_ABBREVIATIONS:
        abbreviated = re.sub(rf"\b{full_term}\b", abbreviation, abbreviated, flags=re.IGNORECASE)
    add_variant(abbreviated)

    return variants


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
    def supports_meaningful_volume(self) -> bool:
        """Borsa Italiana reports real exchange-traded share volume for
        ISIN-quoted stocks/bonds/ETFs (via `ottieni_storico`). The fund-NAV
        path (`codice_fondo` param) never populates volume — that is safely
        handled by MFI/OBV structural validation (insufficient non-null
        observed volume) rather than requiring per-instrument capability
        inference here."""
        return True

    @property
    def volume_kind(self) -> FAVolumeKind:
        return FAVolumeKind.TRADED_SHARES

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
        codice_fondo = (provider_params or {}).get("codice_fondo")
        if codice_fondo:
            # Mutual funds live on the dedicated fund-detail page keyed by the internal
            # BI code; the generic search/scheda page does not resolve a fund by ISIN,
            # so building the URL from the ISIN identifier yields a dead page.
            return f"https://www.borsaitaliana.it/borsa/fondi/dettaglio/{codice_fondo}.html?lang={lingua}"
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
            },
            {
                "key": "codice_fondo",
                "type": "string",
                "required": False,
                "description": "Internal Borsa Italiana fund code (auto-filled for mutual funds; enables NAV pricing when the fund is not on the XMIL market API).",
            },
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

        codice_fondo = (provider_params or {}).get("codice_fondo")
        if codice_fondo:
            return self._fund_current_value(codice_fondo)

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

        codice_fondo = (provider_params or {}).get("codice_fondo")
        if codice_fondo:
            effective_start = ASSET_HISTORY_MIN_FALLBACK if start_date == "min" else start_date
            return self._fund_history_value(codice_fondo, effective_start, end_date)

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

    # ── Fund NAV (mutual funds, priced by internal Borsa Italiana code) ──
    #
    # Mutual funds are NOT on the XMIL market API: their only NAV source is the
    # fund detail page, addressed by an internal code (≠ ISIN) carried in
    # provider_params["codice_fondo"]. That page exposes a single, delayed NAV.

    def _fetch_fund(self, codice_fondo: str) -> DatiFondo:
        """Fetch fund NAV data by internal code, mapping lib errors to AssetSourceError."""
        try:
            return ottieni_dati_fondo(codice_fondo, sessione=_get_session())
        except (StrumentoNonTrovato, DatiNonDisponibili) as e:
            raise AssetSourceError(
                f"No NAV available for fund {codice_fondo} on Borsa Italiana",
                "NO_DATA",
                {"codice_fondo": codice_fondo, "error": str(e)},
            ) from e
        except BorsaItalianaErrore as e:
            raise AssetSourceError(
                f"Failed to fetch NAV for fund {codice_fondo} from Borsa Italiana: {e}",
                "FETCH_ERROR",
                {"codice_fondo": codice_fondo, "error": str(e)},
            ) from e

    def _fund_current_value(self, codice_fondo: str) -> FACurrentValue:
        """Current NAV for a fund — only if the published NAV is dated today.

        A fund NAV is published once per day with a lag. Exposing a stale NAV as the
        "current" value would misstate the portfolio, so when the NAV date is not
        today we raise NO_DATA and let the core fall back to the last-buy estimate.
        """
        dati = self._fetch_fund(codice_fondo)
        if dati.data_nav != date.today():
            raise AssetSourceError(
                f"Fund {codice_fondo} NAV is dated {dati.data_nav}, not today",
                "NO_DATA",
                {"codice_fondo": codice_fondo, "nav_date": str(dati.data_nav)},
            )
        return FACurrentValue(
            value=dati.nav,
            currency=dati.valuta or "EUR",
            as_of_date=dati.data_nav,
            source=self.provider_name,
        )

    def _fund_history_value(self, codice_fondo: str, start: date, end: date) -> FAHistoricalData:
        """Historical NAV for a fund: a single point at the real NAV date.

        The fund page exposes only the latest NAV (no series), dated to the day it
        actually refers to — never date.today(). The core backward-fills the gaps.
        """
        dati = self._fetch_fund(codice_fondo)
        prices: List[FAPricePoint] = []
        if start <= dati.data_nav <= end:
            prices.append(
                FAPricePoint(
                    date=dati.data_nav,
                    open=None,
                    high=None,
                    low=None,
                    close=dati.nav,
                    volume=None,
                    currency=dati.valuta or "EUR",
                    backward_fill_info=None,
                )
            )
        return FAHistoricalData(prices=prices, currency=dati.valuta or "EUR", source=self.provider_name)

    def _fund_search_item(self, dati: DatiFondo, lingua: str, display_name: str | None = None) -> dict:
        """Build a standard search-item dict from fetched fund data.

        The identifier is the real ISIN extracted from the page when available,
        otherwise the internal code as OTHER; provider_params always carries the
        internal code so the asset can be priced by NAV afterwards.
        """
        identifier = dati.isin or dati.codice
        identifier_type = IdentifierType.ISIN if dati.isin else IdentifierType.OTHER
        return {
            "identifier": identifier,
            "identifier_type": identifier_type,
            "display_name": display_name or dati.nome,
            "currency": dati.valuta or "EUR",
            "type": AssetType.FUND.value,
            "provider_params": {"codice_fondo": dati.codice, "language": lingua},
        }

    def _fund_search_items_all_langs(self, dati: DatiFondo) -> list[dict]:
        """Emit the full canonical search-item set for a resolved fund page.

        ``resolve_url`` is only an alternative **entry point** into search: just like
        an on-site ``cerca`` hit, it returns one row per supported language (Italian
        first) with a flag suffix in ``display_name``, so the user picks the language
        exactly as with a normal search result — instead of a single "neutral" row.
        """
        preferred = ("it", "en")
        emit_language_order = tuple(lg for lg in preferred if lg in self.SUPPORTED_LANGUAGES) + tuple(lg for lg in self.SUPPORTED_LANGUAGES if lg not in preferred)
        return [self._fund_search_item(dati, lingua, display_name=f"{dati.nome} {self.LANGUAGE_FLAGS[lingua]}") for lingua in emit_language_order]

    def _scheda_search_items_all_langs(self, isin: str, mic: str | None) -> list[dict] | None:
        """Emit the canonical search-item set for a resolved stock/bond/ETF page.

        Mirrors :meth:`_fund_search_items_all_langs` for ISIN-priced instruments: the
        scheda is fetched once (ISIN, currency and type are language-independent) and
        one row per supported language is emitted with a flag suffix, so a web
        link-finder hit behaves exactly like an on-site ``cerca`` result. Returns
        ``None`` when the page can't be fetched or parsed.
        """
        try:
            scheda = ottieni_scheda(isin, mic, "it", sessione=_get_session())
        except (StrumentoNonTrovato, DatiNonDisponibili):
            return None
        except Exception as e:  # best-effort — never fatal to search
            logger.debug(f"Borsa Italiana resolve_url (scheda) failed for '{isin}': {e}")
            return None
        asset_type = _map_asset_type(scheda.tipo)
        real_isin = scheda.isin or isin
        preferred = ("it", "en")
        emit_language_order = tuple(lg for lg in preferred if lg in self.SUPPORTED_LANGUAGES) + tuple(lg for lg in self.SUPPORTED_LANGUAGES if lg not in preferred)
        return [
            {
                "identifier": real_isin,
                "identifier_type": IdentifierType.ISIN,
                "display_name": f"{scheda.nome} {self.LANGUAGE_FLAGS[lingua]}",
                "currency": scheda.valuta or "EUR",
                "type": asset_type.value if asset_type else scheda.tipo,
                "provider_params": {"language": lingua},
            }
            for lingua in emit_language_order
        ]

    # ── URL resolution (inverse of get_asset_url) ───────────────────────

    @property
    def resolvable_url_domains(self) -> list[str]:
        return ["borsaitaliana.it"]

    async def resolve_url(self, url: str) -> list[dict] | None:
        """Resolve a Borsa Italiana page URL into search-item(s).

        Two page families are recognised, both returning the **same canonical set a
        normal search would emit** — one item per supported language (Italian first,
        with a flag suffix), each carrying the real ISIN and the params needed to price
        the asset afterwards:

        * **Fund detail pages** (``/borsa/fondi/dettaglio/{code}.html``) — NAV-by-code;
          the real ISIN + NAV come from the page, the internal code goes to
          ``provider_params``.
        * **Stock / bond / ETF scheda pages** (``…/scheda/{ISIN}[-{MIC}].html``) —
          priced by ISIN. The ISIN (and optional market segment) is read straight from
          the URL, so the web link-finder can surface instruments the on-site search
          can't match by name (e.g. a BTP searched by its descriptive name).

        Returns ``None`` for anything that is not a recognisable Borsa Italiana page.
        """
        self._check_availability()
        if not url or "borsaitaliana.it" not in url.lower():
            return None
        # Fund detail pages (NAV-by-code): keep the dedicated fund path.
        if estrai_codice_da_url(url):
            try:
                dati = ottieni_dati_fondo_da_url(url, sessione=_get_session())
            except (StrumentoNonTrovato, DatiNonDisponibili):
                return None
            except Exception as e:  # best-effort — never fatal to search
                logger.debug(f"Borsa Italiana resolve_url (fund) failed for '{url}': {e}")
                return None
            return self._fund_search_items_all_langs(dati)
        # Stock / bond / ETF scheda pages keyed by ISIN (optionally ``-MIC``).
        match = _SCHEDA_ISIN_RE.search(url)
        if not match:
            return None
        return self._scheda_search_items_all_langs(match.group(1), match.group(2))

    # ── Search ──────────────────────────────────────────────────────────

    async def search(self, query: str) -> list[dict]:  # noqa: C901 — flat result mapping with language fan-out
        """Search for instruments on Borsa Italiana.

        Emits 2 results per match (EN + IT) with flag emojis,
        similar to JustETF's multi-currency approach.
        """
        self._check_availability()
        try:
            # A single on-site search is enough: borsa's ``cerca`` returns the same instruments
            # (isin, name, type) regardless of the ``lingua`` URL option — that option only selects
            # the localized instrument *page* consulted later (pricing/metadata URL), not the search
            # result set. So we fetch ONCE and emit two rows per instrument (IT + EN) that differ
            # solely by the flag emoji and the downstream ``provider_params.language``. This halves
            # the search network cost versus fetching each language separately.
            preferred = ("it", "en")
            emit_language_order = tuple(lg for lg in preferred if lg in self.SUPPORTED_LANGUAGES) + tuple(lg for lg in self.SUPPORTED_LANGUAGES if lg not in preferred)
            fetch_language = emit_language_order[0] if emit_language_order else "it"

            seen_isins: set[str] = set()
            results: list = []
            for query_variant in _search_query_variants(query):
                for result in cerca(query_variant, lingua=fetch_language, sessione=_get_session()):
                    if result.isin in seen_isins:
                        continue
                    seen_isins.add(result.isin)
                    results.append(result)

            items = []
            fund_cache: dict[str, DatiFondo | None] = {}  # code → fund data, fetched once per search

            # Emit each instrument's language variants together (Italian before English within every
            # group), so the two rows of an instrument never interleave with a sibling.
            for r in results:
                asset_type = _map_asset_type(r.tipo)
                for lingua in emit_language_order:
                    flag = self.LANGUAGE_FLAGS[lingua]

                    if asset_type == AssetType.FUND:
                        # For funds the search API returns the internal code in `isin`,
                        # not a real ISIN; only the fund page holds the real ISIN + NAV.
                        codice = r.isin
                        if codice not in fund_cache:
                            try:
                                fund_cache[codice] = ottieni_dati_fondo(codice, sessione=_get_session())
                            except Exception as e:
                                logger.debug(f"Borsa Italiana: fund page fetch failed for code '{codice}': {e}")
                                fund_cache[codice] = None
                        dati = fund_cache[codice]
                        if dati is not None:
                            items.append(self._fund_search_item(dati, lingua, display_name=f"{r.nome} {flag}"))
                        else:
                            # Fallback: emit with the code as OTHER identifier; pricing still
                            # works via provider_params.codice_fondo.
                            items.append(
                                {
                                    "identifier": codice,
                                    "identifier_type": IdentifierType.OTHER,
                                    "display_name": f"{r.nome} {flag}",
                                    "currency": "EUR",
                                    "type": AssetType.FUND.value,
                                    "provider_params": {"codice_fondo": codice, "language": lingua},
                                }
                            )
                        continue

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

    def _build_fund_description(self, dati: DatiFondo) -> str | None:
        """Compose a fund's short description from the detail-page sections.

        Includes the name, the real ISIN and the non-"N.D." entries scraped from
        the Caratteristiche / Società di Gestione / Costi sections of the fund
        page. The section fields are read defensively (``getattr``) so this
        degrades to just name+ISIN if the installed scraping library predates
        the enriched ``DatiFondo``.
        """
        parts: List[str] = []
        if dati.nome:
            parts.append(dati.nome)
        if dati.isin:
            parts.append(f"ISIN: {dati.isin}")
        for key, value in (getattr(dati, "caratteristiche", None) or {}).items():
            parts.append(f"{key}: {value}")
        for key, value in (getattr(dati, "societa_gestione", None) or {}).items():
            parts.append(f"Società di Gestione — {key}: {value}")
        for key, value in (getattr(dati, "costi", None) or {}).items():
            parts.append(f"Costi — {key}: {value}")
        return " | ".join(parts) if parts else None

    def _fund_metadata(
        self,
        identifier: str,
        identifier_type: IdentifierType,
        codice_fondo: str,
        provider_params: Dict | None,
    ) -> FAAssetPatchItem | None:
        """Build metadata for a mutual fund from its detail page (NAV-by-code funds).

        Funds are not on the XMIL scheda, so the standard ISIN path can't describe
        them; instead we fetch the fund detail page by internal code and derive a
        description from its Caratteristiche / Società di Gestione / Costi sections.
        """
        try:
            dati = self._fetch_fund(codice_fondo)
        except AssetSourceError as e:
            logger.warning(f"Could not fetch fund metadata for code '{codice_fondo}' from Borsa Italiana: {e}")
            return None

        lingua = self._get_lingua(provider_params)
        short_description = self._build_fund_description(dati)
        if short_description and len(short_description) > 500:
            short_description = short_description[:497] + "..."

        classification = FAClassificationParams(short_description=short_description) if short_description else None
        isin = dati.isin or (identifier if identifier_type == IdentifierType.ISIN else None)
        return FAAssetPatchItem(
            asset_id=0,  # Placeholder — caller sets the real ID
            display_name=f"{dati.nome} {self.LANGUAGE_FLAGS[lingua]}",
            currency=dati.valuta or "EUR",
            asset_type=AssetType.FUND,
            classification_params=classification,
            identifier_isin=isin,
            identifier_other=[codice_fondo],
        )

    async def fetch_asset_metadata(  # noqa: C901 — flat metadata mapping with guarded sections
        self,
        identifier: str,
        identifier_type: IdentifierType,
        provider_params: Dict | None = None,
    ) -> FAAssetPatchItem | None:
        """Fetch asset metadata from Borsa Italiana instrument page."""
        self._check_availability()

        # Mutual funds are priced by internal code and are not on the XMIL scheda:
        # route them to the fund-page metadata builder (name + ISIN + Caratteristiche/
        # Società di Gestione/Costi), instead of the ISIN-based scheda path below.
        codice_fondo = (provider_params or {}).get("codice_fondo")
        if codice_fondo:
            return self._fund_metadata(identifier, identifier_type, codice_fondo, provider_params)

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
