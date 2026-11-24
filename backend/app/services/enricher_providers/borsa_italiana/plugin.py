"""The Borsa Italiana enricher (plan 68, C2): the profile of a bond, and the sector of a share, from the instrument page.

It reads the instrument sheet through our library ``borsaItaliana-scraping`` (``ottieni_scheda``) and translates it into
the voices of the profile catalogue; the site search (``cerca``) serves the search. The price provider of the same name
is another plugin: nothing is shared with it (plan §C, rule 1).

What it gives:

- **a bond**: maturity, the coupon (annual and of each period: the annual one computed in ``financial_math`` when the
  page gives only the period's, as for an ordinary BTP), frequency, coupon type, day count, gross and net yield,
  modified duration and accrued interest (these four «as of» the page's reference price date), issuer, issuer type,
  the issuer's country for a state, minimum lot, outstanding amount (in the denomination currency), reference price
  date, payout description, its country and sector, and the legal form. Not the first day of trading: a venue's first
  trading day is not a launch date (a BTP listed years after it was issued);
- **a share**: its sector and the legal form from the sheet; with a library that has ``ottieni_profilo_societa``, also
  the company's description (in the binding's language) and its country (the registered office's) from the «Profilo
  Società» page, both dated by the page's last update (lot BI-PROF). That page is read only when one of its voices is
  asked, with the MIC of the binding or of the sheet's canonical URL (one request more per share); a share without it
  keeps the sheet's voices.

The page comes in the binding's language (``language``, ``en`` or ``it``, as the price provider's): the texts
(frequency, structure, issuer type) are translated from either. A text the plugin does not know leaves its voice empty,
with one log line; «Plain Vanilla» says only that the bond has no special structure (not fixed or floating: that comes
from ESMA's CFI code), so it leaves the coupon type empty without a log line. No description: the page's own sentence
is an advertisement, not prose about the instrument (plan I19): a bond's description is a sentence the plugin composes
from its stable facts (kind, issuer, coupon type and frequency, maturity) in the binding's language.
"""

from __future__ import annotations

import gettext
import re
from collections.abc import Iterable, Iterator, Mapping
from datetime import date
from decimal import Decimal, InvalidOperation
from functools import lru_cache
from typing import Any

import pycountry

from backend.app.db.models import AssetType
from backend.app.logging_config import get_logger
from backend.app.services.assets.base import AssetRateLimitedError
from backend.app.services.enrichers.base import (
    RATE_LIMITED,
    EnricherBinding,
    EnricherPlugin,
    EnricherRateLimited,
    EnricherReadItem,
    EnricherReadStatus,
    EnricherRecognition,
    EnricherSearchResult,
    EnricherTerms,
)
from backend.app.services.enrichers.registry import EnricherRegistry
from backend.app.services.financial_math.interest import annual_coupon_rate
from backend.app.services.platform.provider_registry import register_provider
from backend.app.utils.asset.geo import normalize_country_to_iso3
from backend.app.utils.asset.sector import validate_sector
from backend.app.utils.runtime.pacing import Pacer

try:
    from borsa_italiana_scraping import Sessione, cerca, ottieni_dati_fondo, ottieni_scheda
    from borsa_italiana_scraping.eccezioni import DatiNonDisponibili, RateLimitRaggiunto, StrumentoNonTrovato
except ImportError:  # pragma: no cover — the library is in the lock; without it every call answers «error»
    Sessione = None
    cerca = None
    ottieni_dati_fondo = None
    ottieni_scheda = None

    class DatiNonDisponibili(Exception):  # type: ignore[no-redef]
        """Stand-in when the library is missing."""

    class RateLimitRaggiunto(Exception):  # type: ignore[no-redef]
        """Stand-in when the library is missing."""

    class StrumentoNonTrovato(Exception):  # type: ignore[no-redef]
        """Stand-in when the library is missing."""


try:
    from borsa_italiana_scraping import ottieni_profilo_societa
except ImportError:  # a library older than the company profile (lot BI-PROF): a share keeps the sheet's voices only
    ottieni_profilo_societa = None


logger = get_logger(__name__)

#: One pace for every call of this plugin to borsaitaliana.it, whatever read, «Riconosci» or search it comes from (plan
#: 68, C5; the round-30 rule: the plugin paces its own calls). The library paces the requests inside one session only;
#: this paces two reads at once. Module level: the registry builds a new instance for every call, so a pacer on
#: ``self`` would never be shared. Per process (``utils/runtime/pacing.py``).
_PACER = Pacer(1.0)

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
        "description",
        "geography",
        "sector",
        "legal_form",
    }
)
#: The voices of the company profile page (lot BI-PROF), declared only with a library that reads it.
_PROFILE_VOICES = frozenset({"description", "issuer_country"})
_STOCK_VOICES = frozenset({"sector", "legal_form"}) | (_PROFILE_VOICES if ottieni_profilo_societa is not None else frozenset())
#: A fund page gives little that is the profile's: its currency, its launch date and its management fee («Gestione», C2e:
#: only a part of the TER, so ``management_fee`` and never ``ter``). Not written: the fund's assets (no unit), the
#: management company (not on the recorded page).
_FUND_VOICES = frozenset({"fund_currency", "inception_date", "management_fee"})
_FUND_FEE = "gestione"
#: The identifier type of a fund: Borsa Italiana's internal code (``1FADB716664``), the one its fund page is reached by
#: (searching by ISIN does not find funds); the price assignment stores it as ``codice_fondo``.
FUND_CODE = "BI_FUND_CODE"
_FUND_LAUNCH = "data di partenza"
_SHORT_DATE = re.compile(r"(\d{1,2})/(\d{1,2})/(\d{2}|\d{4})")
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
#: The MIC in a sheet's canonical URL: ``…/borsa/azioni/scheda/IT0003128367-MTAA.html``.
_MIC_IN_URL = re.compile(r"/([A-Z0-9]{12})-([A-Z0-9]{4})\.html(?:$|[?#])", re.IGNORECASE)

# The composed description of a bond (plan I19; wording approved by the consultant): stable facts only, never a price,
# a yield or the annual coupon, which change and would write a new description at every read.
_KIND = {
    "en": {"sovereign": "Government bond", "corporate": "Corporate bond", "supranational": "Supranational bond", None: "Bond"},
    "it": {"sovereign": "Titolo di Stato", "corporate": "Obbligazione societaria", "supranational": "Obbligazione sovranazionale", None: "Obbligazione"},
}
_ISSUER_PART = {"en": "issuer {}", "it": "emittente {}"}
_COUPON_TYPE_PART = {
    "en": {"structured": "structured interest rate", "inflation_linked": "inflation-linked"},
    "it": {"structured": "a tasso strutturato", "inflation_linked": "indicizzato all'inflazione"},
}
_FREQUENCY_PART = {
    "en": {"monthly": "paying monthly", "quarterly": "paying quarterly", "semiannual": "paying semiannually", "annual": "paying annually"},
    "it": {"monthly": "con cedola mensile", "quarterly": "con cedola trimestrale", "semiannual": "con cedola semestrale", "annual": "con cedola annuale"},
}
_MATURITY_PART = {"en": "matures on {}", "it": "scade il {}"}
_MONTH_NAMES = {
    "en": ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"),
    "it": ("gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"),
}


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


def _outstanding_amount(sheet: Any) -> dict[str, Any] | None:
    """The amount outstanding in the bond's denomination currency (the trading currency when the page gives no other);
    none, with one log line, when the two differ: the page does not say which one the amount is in."""
    if sheet.outstanding is None:
        return None
    denomination, trading = _text(sheet.valuta_denominazione), _text(sheet.valuta)
    if denomination is not None and trading is not None and denomination != trading:
        logger.warning("Borsa Italiana outstanding amount left out: two currencies", denomination=denomination, trading=trading, isin=str(sheet.isin))
        return None
    currency = denomination or trading
    return {"amount": sheet.outstanding, "currency": currency} if currency is not None else None


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
        "outstanding_amount": _outstanding_amount(sheet),
        "reference_price_date": sheet.data_prezzo_riferimento,
        "payout_description": _text(sheet.descrizione_payout),
        "geography": {country: "1"} if country is not None else None,
        "sector": {sector: "1"} if sector is not None else None,
        "legal_form": "bond",
    }
    return {key: value for key, value in voices.items() if value is not None}


@lru_cache(maxsize=4)
def _country_translation(language: str) -> gettext.NullTranslations:
    return gettext.translation("iso3166-1", pycountry.LOCALES_DIR, languages=[language], fallback=True)


def _country_name(iso3: str, language: str) -> str | None:
    """A country's name in ``language``, from pycountry's offline translations."""
    country = pycountry.countries.get(alpha_3=iso3)
    if country is None:
        return None
    return country.name if language == "en" else _country_translation(language).gettext(country.name)


def _written_date(day: date, language: str) -> str:
    """«10 October 2028» / «10 ottobre 2028»: the month in words, from a fixed table (never the locale); in Italian the
    first of the month is «1º» (read «primo»)."""
    number = "1º" if language == "it" and day.day == 1 else str(day.day)
    return f"{number} {_MONTH_NAMES[language][day.month - 1]} {day.year}"


def _maturity_part(day: date, language: str) -> str:
    """«matures on 1 May 2031» / «scade il 1º maggio 2031», «scade l'8 maggio …»: the article elides before 8 and 11."""
    if language == "it" and day.day in (8, 11):
        return f"scade l'{_written_date(day, language)}"
    return _MATURITY_PART[language].format(_written_date(day, language))


def compose_description(voices: Mapping[str, Any], language: str) -> str | None:
    """The sentence that describes a bond from its stable voices, in ``language``: kind, issuer, coupon type and
    frequency, then its maturity. None when nothing beyond the kind is known: «Bond.» says nothing, and a source with
    nothing to say must not replace the text that was there (plan §12)."""
    country = voices.get("issuer_country")
    issuer = (_country_name(country, language) if country is not None else None) or voices.get("issuer_name")
    facts = [
        _ISSUER_PART[language].format(issuer) if issuer else None,
        _COUPON_TYPE_PART[language].get(voices.get("coupon_type")),
        _FREQUENCY_PART[language].get(voices.get("coupon_frequency")),
    ]
    maturity = voices.get("maturity_date")
    if maturity is None and not any(facts):
        return None
    sentence = ", ".join(part for part in [_KIND[language].get(voices.get("issuer_type"), _KIND[language][None]), *facts] if part)
    if maturity is not None:
        sentence += "; " + _maturity_part(maturity, language)
    return sentence + "."


def sheet_voices(sheet: Any, language: str = _DEFAULT_LANGUAGE) -> dict[str, Any]:
    """The voices of any sheet, read in ``language``: a bond's (with its composed description), a share's (its sector
    and legal form), nothing for another instrument."""
    kind = _text(sheet.tipo)
    if kind == "obbligazione":
        voices = bond_voices(sheet)
        description = compose_description(voices, language)
        return {**voices, "description": description} if description is not None else voices
    if kind == "azione":
        return {"legal_form": "share", **({"sector": {sector: "1"}} if (sector := _share_sector(sheet)) is not None else {})}
    return {}


def _share_sector(sheet: Any) -> str | None:
    """A share's sector when the generic helper knows the page's name; else none (a single sector the helper does not
    know would be stored as «Other» at 100 %, which says nothing). The helper writes the one log line naming it."""
    sector = _text(sheet.settore)
    return sector if sector is None or validate_sector(sector) else None


def profile_voices(profile: Any) -> dict[str, Any]:
    """The voices of a company profile page: its description, and its country (the registered office's, as an ISO 3166
    alpha-3 code through the generic helper; a name the helper does not know leaves it out with one log line)."""
    voices: dict[str, Any] = {}
    description = _text(profile.descrizione)
    if description is not None:
        voices["description"] = description
    address = profile.indirizzo
    country = _text(address.paese) if address is not None else None
    if country is not None:
        try:
            voices["issuer_country"] = normalize_country_to_iso3(country)
        except ValueError:  # parsing probe: a country name the helper does not know
            logger.warning("Borsa Italiana country not translated, voice left out", field="issuer_country", value=country, isin=str(profile.isin))
    return voices


def profile_source_dates(profile: Any, voices: Mapping[str, Any]) -> dict[str, date]:
    """The page's last update on the voices it gave."""
    day = profile.ultimo_aggiornamento
    return dict.fromkeys(voices, day) if day is not None else {}


def _sheet_mic(binding: EnricherBinding, sheet: Any) -> str | None:
    """The market of a share: the binding's ``mic``, else the one in the sheet's canonical URL."""
    mic = _text(binding.params.get("mic"))
    if mic is not None:
        return mic.upper()
    match = _MIC_IN_URL.search(_text(sheet.url_pagina) or "")
    return match.group(2).upper() if match is not None else None


def _launch_date(value: Any) -> date | None:
    """«14/03/22» → 2022-03-14 (a two-digit year in this century up to this year, else the last), «14/03/2022» too."""
    match = _SHORT_DATE.fullmatch(_text(value) or "")
    if match is None:
        return None
    day, month, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
    if len(match.group(3)) == 2:
        year += 2000 if year <= date.today().year % 100 else 1900
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _management_fee(text: Any) -> str | None:
    """«Gestione» («0.4», «0,40», «0.4%»: a percentage per year) as a fraction («0.004»); None when it is not a
    non-negative number (N.D., empty, a text)."""
    if not isinstance(text, str):
        return None
    cleaned = text.strip().removesuffix("%").strip().replace(",", ".")
    try:
        value = Decimal(cleaned)
    except InvalidOperation:  # parsing probe: a text that is no number is no fee
        return None
    if not value.is_finite() or value < 0:
        return None
    return str(value / 100)


def fund_voices(fund: Any) -> dict[str, Any]:
    """The catalogue voices of a fund page: its currency, its launch date («Data di partenza») and its management fee
    («Gestione», C2e)."""
    characteristics = {str(key).strip().lower(): value for key, value in (fund.caratteristiche or {}).items()}
    costs = {str(key).strip().lower(): value for key, value in (fund.costi or {}).items()}
    voices = {
        "fund_currency": _text(fund.valuta),
        "inception_date": _launch_date(characteristics.get(_FUND_LAUNCH)),
        "management_fee": _management_fee(costs.get(_FUND_FEE)),
    }
    return {key: value for key, value in voices.items() if value is not None}


def _fund_code(binding: EnricherBinding) -> str | None:
    """The internal fund code a binding reads by: its identifier for a ``BI_FUND_CODE`` binding, its ``codice_fondo``
    parameter for an ISIN one (the price assignment's shape); None for a sheet."""
    if binding.identifier_type == FUND_CODE:
        return _text(binding.identifier)
    if binding.identifier_type == "ISIN":
        return _text(binding.params.get("codice_fondo"))
    return None


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
    accepted_identifier_types = ("ISIN", FUND_CODE)
    voices = {AssetType.BOND: _BOND_VOICES, AssetType.STOCK: _STOCK_VOICES, AssetType.FUND: _FUND_VOICES}
    #: Bonds and funds first; for shares Yahoo leads (C3), Borsa Italiana gives the sector of the ones listed in Milan.
    default_priority = {asset_type: {AssetType.BOND: 10, AssetType.FUND: 10, AssetType.STOCK: 20}.get(asset_type) for asset_type in AssetType}

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
            {"key": "codice_fondo", "type": "string", "required": False, "label": "Fund internal code", "x-i18n-key": "enrichers.borsa_italiana.params.codice_fondo"},
        ]

    @property
    def test_cases(self) -> list[dict]:
        return [
            {"binding": {"identifier_type": "ISIN", "identifier": "IT0005565400"}, "asset_type": AssetType.BOND.value},  # BTP Valore Oct 2028
            {"binding": {"identifier_type": "ISIN", "identifier": "IT0003128367"}, "asset_type": AssetType.STOCK.value},  # Enel
            {"binding": {"identifier_type": FUND_CODE, "identifier": "1FADB716664"}, "asset_type": AssetType.FUND.value},  # Anima Dinamix
        ]

    def page_url(self, binding: EnricherBinding) -> str | None:
        code = _fund_code(binding)
        if code is not None:
            # A fund lives on its detail page, by the internal code: the search page does not resolve a fund's ISIN
            return f"https://www.borsaitaliana.it/borsa/fondi/dettaglio/{code}.html?lang={_language(binding)}"
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
        _PACER.wait()
        return ottieni_scheda(binding.identifier, params.get("mic"), _language(binding), sessione=session, platform=params.get("platform"))

    @staticmethod
    def _fund(code: str, session: Any = None) -> Any:
        if ottieni_dati_fondo is None:
            raise RuntimeError("borsa-italiana-scraping is not installed")
        _PACER.wait()
        return ottieni_dati_fondo(code, sessione=session)

    @staticmethod
    def _profile(binding: EnricherBinding, sheet: Any, session: Any = None) -> Any:
        _PACER.wait()
        return ottieni_profilo_societa(str(sheet.isin or binding.identifier), _sheet_mic(binding, sheet), _language(binding), sessione=session)

    def recognize(self, binding: EnricherBinding) -> EnricherRecognition:
        code = _fund_code(binding)
        if code is not None:
            return self._recognize_fund(binding, code)
        if binding.identifier_type != "ISIN":
            return EnricherRecognition(found=False)
        try:
            sheet = self._sheet(binding)
        except StrumentoNonTrovato:  # «not resolved» too: a page the site does not give for this ISIN
            return EnricherRecognition(found=False)
        except RateLimitRaggiunto as error:
            raise AssetRateLimitedError(f"Borsa Italiana refused for too many requests: {error}") from error
        return EnricherRecognition(found=True, name=_text(sheet.nome), page_url=_text(sheet.url_pagina) or self.page_url(binding))

    def _recognize_fund(self, binding: EnricherBinding, code: str) -> EnricherRecognition:
        try:
            fund = self._fund(code)
        except (StrumentoNonTrovato, DatiNonDisponibili):
            return EnricherRecognition(found=False)
        except RateLimitRaggiunto as error:
            raise AssetRateLimitedError(f"Borsa Italiana refused for too many requests: {error}") from error
        isin = _text(fund.isin)
        # The page's ISIN is a strong identifier: the cascade goes on with it to the other enrichers (B4)
        return EnricherRecognition(found=True, name=_text(fund.nome), page_url=_text(fund.url) or self.page_url(binding), identifiers={"ISIN": isin} if isin else {})

    def read(self, bindings: list[EnricherBinding], keys: Iterable[str] | None = None) -> Iterator[EnricherReadItem]:
        # One library session for the whole read: it keeps the site's cookies and paces its own requests; closed
        # whatever ends the read (a failure, or the consumer stopping it early)
        session = Sessione() if Sessione is not None else None
        try:
            yield from self._read_with(session, bindings, None if keys is None else frozenset(keys))
        finally:
            if session is not None:
                session.chiudi()

    def _read_with(self, session: Any, bindings: list[EnricherBinding], keys: frozenset[str] | None) -> Iterator[EnricherReadItem]:  # noqa: C901 — one flat loop: the outcome of each binding
        refused = False
        for index, binding in enumerate(bindings):
            code = _fund_code(binding)
            if code is None and binding.identifier_type != "ISIN":
                yield EnricherReadItem(index=index, status=EnricherReadStatus.NOT_FOUND)
                continue
            if refused:
                yield EnricherReadItem(index=index, status=EnricherReadStatus.ERROR, error_code=RATE_LIMITED)
                continue
            try:
                if code is not None:
                    try:
                        fund = self._fund(code, session)
                    except DatiNonDisponibili:  # a fund page without its data: not found, as a missing one
                        yield EnricherReadItem(index=index, status=EnricherReadStatus.NOT_FOUND)
                        continue
                    yield EnricherReadItem(index=index, status=EnricherReadStatus.OK, values=fund_voices(fund))
                    continue
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
            values = sheet_voices(sheet, _language(binding))
            dates = sheet_source_dates(sheet, values)
            if _text(sheet.tipo) == "azione" and ottieni_profilo_societa is not None and (keys is None or keys & _PROFILE_VOICES):
                try:
                    profile = self._profile(binding, sheet, session)
                except StrumentoNonTrovato:  # «not resolved» too: no profile page for this share, the sheet's voices stay
                    profile = None
                except RateLimitRaggiunto as error:
                    refused = True
                    logger.warning("Borsa Italiana refused for too many requests", isin=binding.identifier, error=str(error))
                    yield EnricherReadItem(index=index, status=EnricherReadStatus.ERROR, error_code=RATE_LIMITED)
                    continue
                except Exception as error:  # noqa: BLE001 — isolation boundary: a failing profile leaves the sheet's voices
                    logger.warning("Borsa Italiana company profile failed", isin=binding.identifier, exc_info=error)
                    profile = None
                if profile is not None:
                    extra = profile_voices(profile)
                    values = {**values, **extra}
                    dates = {**dates, **profile_source_dates(profile, extra)}
            yield EnricherReadItem(index=index, status=EnricherReadStatus.OK, values=values, source_dates=dates)

    def search(self, query: str) -> list[EnricherSearchResult]:
        if cerca is None:
            raise RuntimeError("borsa-italiana-scraping is not installed")
        session = Sessione()
        try:
            _PACER.wait()
            hits = cerca(query, lingua="it", sessione=session)
        except RateLimitRaggiunto as error:
            raise EnricherRateLimited("Borsa Italiana refused the search for too many requests") from error
        finally:
            session.chiudi()
        results: list[EnricherSearchResult] = []
        for hit in hits:
            binding = EnricherBinding(identifier_type="ISIN", identifier=hit.isin, params={"mic": hit.mic})
            asset_type = _SHEET_ASSET_TYPES.get((_text(hit.tipo) or "").lower())
            results.append(EnricherSearchResult(name=hit.nome, binding=binding, asset_type=asset_type, page_url=self.page_url(binding)))
        return results
