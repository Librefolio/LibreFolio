"""The Borsa Italiana enricher (plan 68, C2): the profile of a bond, and the sector of a share, from the instrument page.

It reads the instrument sheet through our library ``borsaItaliana-scraping`` (``ottieni_scheda``) and translates it into
the voices of the profile catalogue; the site search (``cerca``) serves the search. The price provider of the same name
is another plugin: nothing is shared with it (plan §C, rule 1).

What it gives:

- **a bond**: maturity, the coupon (annual and of each period: the annual one computed in ``financial_math`` when the
  page gives only the period's, as for an ordinary BTP), frequency, coupon type, day count, gross and net yield,
  modified duration and accrued interest (these four «as of» the page's reference price date), issuer, issuer type,
  the issuer's country for a state, minimum lot, outstanding amount, reference price date, payout description, the
  first day of trading, its country and sector, and the legal form;
- **a share**: its sector and the legal form.

The page comes in the binding's language (``language``, ``en`` or ``it``, as the price provider's): the texts
(frequency, structure, issuer type) are translated from either. A text the plugin does not know leaves its voice empty,
with one log line; «Plain Vanilla» says only that the bond has no special structure (not fixed or floating: that comes
from ESMA's CFI code), so it leaves the coupon type empty without a log line. No description: the page's own sentence
is an advertisement, not prose about the instrument (plan I19); a sentence composed from the data comes later.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping
from datetime import date
from decimal import Decimal
from typing import Any

from backend.app.db.models import AssetType
from backend.app.logging_config import get_logger
from backend.app.services.assets.base import AssetRateLimitedError
from backend.app.services.enrichers.base import (
    RATE_LIMITED,
    EnricherBinding,
    EnricherPlugin,
    EnricherReadItem,
    EnricherReadStatus,
    EnricherRecognition,
    EnricherSearchResult,
    EnricherTerms,
)
from backend.app.services.enrichers.registry import EnricherRegistry
from backend.app.services.financial_math.interest import annual_coupon_rate
from backend.app.services.platform.provider_registry import register_provider
from backend.app.utils.asset.sector import validate_sector

try:
    from borsa_italiana_scraping import Sessione, cerca, ottieni_scheda
    from borsa_italiana_scraping.eccezioni import RateLimitRaggiunto, StrumentoNonTrovato
except ImportError:  # pragma: no cover — the library is in the lock; without it every call answers «error»
    Sessione = None
    cerca = None
    ottieni_scheda = None

    class RateLimitRaggiunto(Exception):  # type: ignore[no-redef]
        """Stand-in when the library is missing."""

    class StrumentoNonTrovato(Exception):  # type: ignore[no-redef]
        """Stand-in when the library is missing."""


logger = get_logger(__name__)

#: The error code of a read the library or the site failed (not a refusal for too many requests).
SOURCE_ERROR = "SOURCE_ERROR"
_LANGUAGES = ("en", "it")
_DEFAULT_LANGUAGE = "en"
_HUNDRED = Decimal(100)

_BOND_VOICES = frozenset(
    {
        "maturity_date",
        "coupon_rate",
        "coupon_period_rate",
        "coupon_frequency",
        "coupon_type",
        "day_count",
        "yield_gross",
        "yield_net",
        "modified_duration",
        "accrued_interest",
        "issuer_name",
        "issuer_type",
        "issuer_country",
        "min_lot",
        "outstanding_amount",
        "reference_price_date",
        "payout_description",
        "inception_date",
        "geography",
        "sector",
        "legal_form",
    }
)
_STOCK_VOICES = frozenset({"sector", "legal_form"})
#: The bond figures the page gives «as of» its reference price date.
_AS_OF_REFERENCE_PRICE = ("yield_gross", "yield_net", "modified_duration", "accrued_interest")

# The page's texts, in either language, lower case → catalogue code. Rows marked «no recording» come from the site's
# wording elsewhere, not from a recorded page.
_FREQUENCY = {
    "monthly": "monthly",  # no recording
    "quarterly": "quarterly",
    "semiannually": "semiannual",
    "annually": "annual",
    "12 months": "annual",  # EuroTLX
    "6 months": "semiannual",  # no recording
    "3 months": "quarterly",  # no recording
    "1 month": "monthly",  # no recording
    "mensile": "monthly",  # no recording
    "trimestrale": "quarterly",
    "semestrale": "semiannual",
    "annuale": "annual",
}
#: None: a known text that fills no coupon type («Plain Vanilla»: no special structure, not fixed or floating).
_COUPON_TYPE: dict[str, str | None] = {
    "structured interest rate": "structured",
    "stuctured interest rate": "structured",  # the Italian page's misspelling
    "inflation linked": "inflation_linked",
    "titoli indicizzati all'inflazione": "inflation_linked",
    "plain vanilla": None,
}
_DAY_COUNT = {
    "act/act (icma)": "act_act_icma",
    "act/act (periodic basis)": "act_act_icma",  # the same method, per coupon period
}
_ISSUER_TYPE = {
    "italian government bonds": "sovereign",
    "titoli di stato italiani": "sovereign",
    "foreign public debt": "sovereign",
    "titoli di stato esteri": "sovereign",
    "obbligazioni finanziarie": "corporate",
    "corporate bonds": "corporate",  # no recording
    "supranational bonds": "supranational",  # no recording
    "obbligazioni sovranazionali": "supranational",  # no recording
}
#: The sector of a bond by its issuer type (the standard sectors of ``utils/asset/sector.py``).
_SECTOR_OF_ISSUER_TYPE = {"sovereign": "Government Bonds", "corporate": "Corporate Bonds"}
#: A state issuer → its ISO 3166 alpha-3 country. Only states: a company's country is never guessed from its name.
_STATE_ISSUERS = {
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
_SHEET_ASSET_TYPES = {"obbligazione": AssetType.BOND, "azione": AssetType.STOCK}


def _text(value: Any) -> str | None:
    return value.strip() or None if isinstance(value, str) else None


def _translated(table: Mapping[str, str | None], value: Any, field: str, isin: str) -> str | None:
    """The catalogue code of a page text; None, with one log line, for a text the table does not know."""
    text = _text(value)
    if text is None:
        return None
    key = text.lower()
    if key not in table:
        logger.warning("Borsa Italiana value not translated, voice left out", field=field, value=text, isin=isin)
        return None
    return table[key]


def _fraction(percent: Decimal | None) -> Decimal | None:
    return percent / _HUNDRED if percent is not None else None


def _coupon_rate(sheet: Any, frequency: str | None) -> Decimal | None:
    """The annual coupon as a fraction: the page's, or the coupon of each period × the coupons a year."""
    if sheet.cedola_annua is not None:
        return _fraction(sheet.cedola_annua)
    if sheet.cedola_periodale is None or frequency is None:
        return None
    return _fraction(annual_coupon_rate(sheet.cedola_periodale, frequency))


def bond_voices(sheet: Any) -> dict[str, Any]:
    """The catalogue voices of a bond's sheet, as raw values; a voice the sheet does not give is absent."""
    isin = str(sheet.isin)
    frequency = _translated(_FREQUENCY, sheet.frequenza_cedola, "coupon_frequency", isin)
    issuer = _text(sheet.emittente)
    issuer_type = _translated(_ISSUER_TYPE, sheet.tipologia, "issuer_type", isin) if _text(sheet.tipologia) else None
    country = _STATE_ISSUERS.get(issuer.lower()) if issuer is not None and issuer_type == "sovereign" else None
    sector = _SECTOR_OF_ISSUER_TYPE.get(issuer_type) if issuer_type is not None else None
    voices: dict[str, Any] = {
        "maturity_date": sheet.scadenza,
        "coupon_rate": _coupon_rate(sheet, frequency),
        "coupon_period_rate": _fraction(sheet.cedola_periodale),
        "coupon_frequency": frequency,
        "coupon_type": _translated(_COUPON_TYPE, sheet.struttura_bond, "coupon_type", isin),
        "day_count": _translated(_DAY_COUNT, sheet.convenzione_giorni, "day_count", isin),
        "yield_gross": _fraction(sheet.rendimento_lordo),
        "yield_net": _fraction(sheet.rendimento_netto),
        "modified_duration": sheet.duration_modificata,  # years
        "accrued_interest": sheet.rateo_lordo,  # per 100 of nominal
        "issuer_name": issuer,
        "issuer_type": issuer_type,
        "issuer_country": country,
        "min_lot": sheet.lotto_minimo,
        "outstanding_amount": {"amount": sheet.outstanding, "currency": sheet.valuta} if sheet.outstanding is not None and sheet.valuta else None,
        "reference_price_date": sheet.data_prezzo_riferimento,
        "payout_description": _text(sheet.descrizione_payout),
        "inception_date": sheet.data_primo_giorno,  # the first day of trading: the listing date
        "geography": {country: "1"} if country is not None else None,
        "sector": {sector: "1"} if sector is not None else None,
        "legal_form": "bond",
    }
    return {key: value for key, value in voices.items() if value is not None}


def sheet_voices(sheet: Any) -> dict[str, Any]:
    """The voices of any sheet: a bond's, a share's (its sector and legal form), nothing for another instrument."""
    kind = _text(sheet.tipo)
    if kind == "obbligazione":
        return bond_voices(sheet)
    if kind == "azione":
        return {"legal_form": "share", **({"sector": {sector: "1"}} if (sector := _share_sector(sheet)) is not None else {})}
    return {}


def _share_sector(sheet: Any) -> str | None:
    """A share's sector when the generic helper knows the page's name; else none (a single sector the helper does not
    know would be stored as «Other» at 100 %, which says nothing). The helper writes the one log line naming it."""
    sector = _text(sheet.settore)
    return sector if sector is None or validate_sector(sector) else None


def sheet_source_dates(sheet: Any, voices: Mapping[str, Any]) -> dict[str, date]:
    """The reference price date on the bond figures that are «as of» it."""
    day = sheet.data_prezzo_riferimento
    return {key: day for key in _AS_OF_REFERENCE_PRICE if key in voices} if day is not None else {}


def _language(binding: EnricherBinding) -> str:
    language = binding.params.get("language")
    return language if language in _LANGUAGES else _DEFAULT_LANGUAGE


@register_provider(EnricherRegistry)
class BorsaItalianaEnricher(EnricherPlugin):
    """The profile of a bond, and the sector of a share, from its page on Borsa Italiana."""

    code = "borsa_italiana"
    name = "Borsa Italiana"
    icon = "https://www.borsaitaliana.it/media-rwd/assets/images/favicon.ico"
    terms = EnricherTerms.PRICE_SOURCE
    accepted_identifier_types = ("ISIN",)
    voices = {AssetType.BOND: _BOND_VOICES, AssetType.STOCK: _STOCK_VOICES}
    #: Bonds first; for shares Yahoo leads (C3), Borsa Italiana gives the sector of the ones listed in Milan.
    default_priority = {asset_type: {AssetType.BOND: 10, AssetType.STOCK: 20}.get(asset_type) for asset_type in AssetType}

    @property
    def params_schema(self) -> list[dict]:
        # The binding's parameters, as the price provider's: the page's language, and the market for EuroTLX
        return [
            {
                "key": "language",
                "type": "select",
                "required": False,
                "options": list(_LANGUAGES),
                "default": _DEFAULT_LANGUAGE,
                "label": "Language",
                "x-i18n-key": "enrichers.borsa_italiana.params.language",
            },
            {"key": "mic", "type": "string", "required": False, "label": "Market MIC", "x-i18n-key": "enrichers.borsa_italiana.params.mic"},
            {"key": "platform", "type": "string", "required": False, "label": "Platform", "x-i18n-key": "enrichers.borsa_italiana.params.platform"},
        ]

    @property
    def test_cases(self) -> list[dict]:
        return [
            {"binding": {"identifier_type": "ISIN", "identifier": "IT0005565400"}, "asset_type": AssetType.BOND.value},  # BTP Valore Oct 2028
            {"binding": {"identifier_type": "ISIN", "identifier": "IT0003128367"}, "asset_type": AssetType.STOCK.value},  # Enel
        ]

    def page_url(self, binding: EnricherBinding) -> str | None:
        url = f"https://www.borsaitaliana.it/borsa/search/scheda.html?code={binding.identifier}&lang={_language(binding)}"
        mic = binding.params.get("mic")
        platform = binding.params.get("platform")
        if mic:
            url += f"&mic={mic}"
        if platform:
            url += f"&platform={platform}"
        return url

    @staticmethod
    def _sheet(binding: EnricherBinding, session: Any = None) -> Any:
        if ottieni_scheda is None:
            raise RuntimeError("borsa-italiana-scraping is not installed")
        params = binding.params
        return ottieni_scheda(binding.identifier, params.get("mic"), _language(binding), sessione=session, platform=params.get("platform"))

    def recognize(self, binding: EnricherBinding) -> EnricherRecognition:
        if binding.identifier_type != "ISIN":
            return EnricherRecognition(found=False)
        try:
            sheet = self._sheet(binding)
        except StrumentoNonTrovato:  # «not resolved» too: a page the site does not give for this ISIN
            return EnricherRecognition(found=False)
        except RateLimitRaggiunto as error:
            raise AssetRateLimitedError(f"Borsa Italiana refused for too many requests: {error}") from error
        return EnricherRecognition(found=True, name=_text(sheet.nome), page_url=_text(sheet.url_pagina) or self.page_url(binding))

    def read(self, bindings: list[EnricherBinding], keys: Iterable[str] | None = None) -> Iterator[EnricherReadItem]:
        # One library session for the whole read: it keeps the site's cookies and paces its own requests; closed
        # whatever ends the read (a failure, or the consumer stopping it early)
        session = Sessione() if Sessione is not None else None
        try:
            yield from self._read_with(session, bindings)
        finally:
            if session is not None:
                session.chiudi()

    def _read_with(self, session: Any, bindings: list[EnricherBinding]) -> Iterator[EnricherReadItem]:
        refused = False
        for index, binding in enumerate(bindings):
            if binding.identifier_type != "ISIN":
                yield EnricherReadItem(index=index, status=EnricherReadStatus.NOT_FOUND)
                continue
            if refused:
                yield EnricherReadItem(index=index, status=EnricherReadStatus.ERROR, error_code=RATE_LIMITED)
                continue
            try:
                sheet = self._sheet(binding, session)
            except StrumentoNonTrovato:
                yield EnricherReadItem(index=index, status=EnricherReadStatus.NOT_FOUND)
                continue
            except RateLimitRaggiunto as error:
                refused = True
                logger.warning("Borsa Italiana refused for too many requests", isin=binding.identifier, error=str(error))
                yield EnricherReadItem(index=index, status=EnricherReadStatus.ERROR, error_code=RATE_LIMITED)
                continue
            except Exception as error:  # noqa: BLE001 — isolation boundary: one instrument's failure is that instrument's outcome
                logger.warning("Borsa Italiana read failed", isin=binding.identifier, exc_info=error)
                yield EnricherReadItem(index=index, status=EnricherReadStatus.ERROR, error_code=SOURCE_ERROR, error_message=type(error).__name__)
                continue
            values = sheet_voices(sheet)
            yield EnricherReadItem(index=index, status=EnricherReadStatus.OK, values=values, source_dates=sheet_source_dates(sheet, values))

    def search(self, query: str) -> list[EnricherSearchResult]:
        if cerca is None:
            raise RuntimeError("borsa-italiana-scraping is not installed")
        session = Sessione()
        try:
            hits = cerca(query, lingua="it", sessione=session)
        finally:
            session.chiudi()
        results: list[EnricherSearchResult] = []
        for hit in hits:
            binding = EnricherBinding(identifier_type="ISIN", identifier=hit.isin, params={"mic": hit.mic})
            asset_type = _SHEET_ASSET_TYPES.get((_text(hit.tipo) or "").lower())
            results.append(EnricherSearchResult(name=hit.nome, binding=binding, asset_type=asset_type, page_url=self.page_url(binding)))
        return results
