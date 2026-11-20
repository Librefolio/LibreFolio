"""The ESMA enricher (plan 68, C4b): the facts an official register gives about an instrument, by ISIN.

It reads FIRDS, the register of financial instruments of the European Securities and Markets Authority, through our
library ``esma-registers`` (``find_instrument``: one call per ISIN, the register's rows of every market reduced to one).
The register gives few facts, but official ones, for every instrument traded on a European market:

- **every instrument**: the issuer's LEI (``issuer_lei``), which «Riconosci» also hands to the other enrichers (B4);
- **from the CFI code** (ISO 10962, six letters), the legal form and, for a bond, the type of interest and who guarantees
  it; for a fund, its distribution policy (``cfi_voices``). The research's table (``prove-arricchitori-PROF.md`` §5.1);
- **a bond**: its maturity, and its annual coupon **only for a fixed rate**. For BTP Italia and BTP Valore the
  register's «fixed rate» is the coupon of one period, and their CFI says variable: never written as the yearly rate.

It comes after the sources of each type (degree 30): a fund's distribution policy is justETF's first, a bond's facts
Borsa Italiana's. The register has no page per instrument (``page_url`` is None); ``help_url`` is its search page.
Terms: ESMA's legal notice allows reproducing its information with the source cited, and says nothing of the registers
or of automated reading: the class is ``open`` (an official register), with that reservation in the library's README.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
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
    EnricherTerms,
)
from backend.app.services.enrichers.registry import EnricherRegistry
from backend.app.services.platform.provider_registry import register_provider
from backend.app.utils.runtime.pacing import Pacer

try:
    from esma_registers import InvalidIsin, RateLimited, find_instrument, normalize_isin
except ImportError:  # pragma: no cover — the library is in the lock; without it every call answers «error»
    find_instrument = None
    normalize_isin = None

    class InvalidIsin(Exception):  # type: ignore[no-redef]
        """Stand-in when the library is missing."""

    class RateLimited(Exception):  # type: ignore[no-redef]
        """Stand-in when the library is missing."""

        retry_after: float | None = None


logger = get_logger(__name__)

#: One pace for every call of this plugin to the register, whatever read or «Riconosci» it comes from (C5). Module
#: level: the registry builds a new instance for every call. Per process (``utils/runtime/pacing.py``).
_PACER = Pacer(1.0)
#: The error code of a read the register failed (not a refusal for too many requests).
SOURCE_ERROR = "SOURCE_ERROR"
_DEGREE = 30
_HUNDRED = Decimal(100)

_ETF_FAMILY = frozenset(asset_type for asset_type in AssetType if asset_type == AssetType.ETF or asset_type.value.startswith("ETF_"))
_FUND_VOICES = frozenset({"issuer_lei", "distribution_policy"})
_VOICES = {
    AssetType.STOCK: frozenset({"issuer_lei", "legal_form"}),
    AssetType.BOND: frozenset({"issuer_lei", "legal_form", "maturity_date", "coupon_type", "coupon_rate", "issuer_type"}),
    AssetType.FUND: _FUND_VOICES,
    AssetType.COMMODITY: frozenset({"issuer_lei", "legal_form"}),
    **dict.fromkeys(_ETF_FAMILY, _FUND_VOICES),
}

#: The first two letters of the CFI code (category and group) → ``legal_form``. A fund's ``C…`` does not say whether it
#: is a UCITS: no legal form for it.
_LEGAL_FORM = {"ES": "share", "DB": "bond", "EY": "etc_etn"}
#: A bond (``DB``): its first attribute, the type of interest → ``coupon_type``.
_COUPON_TYPE = {"F": "fixed", "V": "floating", "Z": "zero_coupon"}
#: A bond (``DB``): its second attribute, the guarantee or ranking → ``issuer_type``. Only the two that name the issuer's
#: kind; «senior», «secured» and the others say how the debt ranks, not who issued it.
_ISSUER_TYPE = {"T": "sovereign", "C": "supranational"}
#: A fund (``CE`` an ETF, ``CI`` a standard fund): its second attribute, the distribution policy.
_DISTRIBUTION = {"G": "accumulating", "I": "distributing"}


def cfi_voices(cfi: str | None) -> dict[str, str]:
    """The voices a CFI code says, in their stored form."""
    code = (cfi or "").strip().upper()
    if len(code) != 6:
        return {}
    voices: dict[str, str] = {}
    if (legal_form := _LEGAL_FORM.get(code[:2])) is not None:
        voices["legal_form"] = legal_form
    if code[:2] == "DB":
        if (issuer_type := _ISSUER_TYPE.get(code[3])) is not None:
            voices["issuer_type"] = issuer_type
        if (coupon_type := _COUPON_TYPE.get(code[2])) is not None:
            voices["coupon_type"] = coupon_type
    if code[:2] in ("CE", "CI") and (policy := _DISTRIBUTION.get(code[3])) is not None:
        voices["distribution_policy"] = policy
    return voices


def instrument_voices(instrument: Any) -> dict[str, str]:
    """The voices of one instrument of the register, in their stored form."""
    voices = cfi_voices(instrument.cfi_code)
    if instrument.issuer_lei:
        voices["issuer_lei"] = instrument.issuer_lei
    if voices.get("legal_form") == "bond":
        if instrument.maturity_date is not None:
            voices["maturity_date"] = instrument.maturity_date.isoformat()
        if voices.get("coupon_type") == "fixed" and instrument.fixed_rate is not None:
            voices["coupon_rate"] = format((instrument.fixed_rate / _HUNDRED).normalize(), "f")
    return voices


def _isin(binding: EnricherBinding) -> str | None:
    """The binding's ISIN, checked; None for any other identifier or an invalid ISIN (the register cannot have it)."""
    if binding.identifier_type != "ISIN" or normalize_isin is None:
        return None
    try:
        return normalize_isin(binding.identifier)
    except InvalidIsin:
        return None


@register_provider(EnricherRegistry)
class EsmaEnricher(EnricherPlugin):
    """An instrument's identity facts from ESMA's FIRDS register."""

    code = "esma"
    name = "ESMA (FIRDS)"
    icon = "https://www.esma.europa.eu/themes/custom/esma_webst_theme/favicon.ico"
    help_url = "https://registers.esma.europa.eu/publication/searchRegister?core=esma_registers_firds"
    terms = EnricherTerms.OPEN
    accepted_identifier_types = ("ISIN",)
    voices = _VOICES
    #: After the sources of each type: the register's facts fill what they leave empty.
    default_priority = {asset_type: _DEGREE if asset_type in _VOICES else None for asset_type in AssetType}

    @property
    def test_cases(self) -> list[dict]:
        return [
            {"binding": {"identifier_type": "ISIN", "identifier": "IT0003128367"}, "asset_type": AssetType.STOCK.value},  # Enel
            {"binding": {"identifier_type": "ISIN", "identifier": "IT0005441883"}, "asset_type": AssetType.BOND.value},  # BTP 2.15% 2072
            {"binding": {"identifier_type": "ISIN", "identifier": "IE00B4L5Y983"}, "asset_type": AssetType.ETF.value},  # iShares Core MSCI World
        ]

    def page_url(self, binding: EnricherBinding) -> str | None:
        return None

    @staticmethod
    def _find(isin: str) -> Any:
        if find_instrument is None:
            raise RuntimeError("esma-registers is not installed")
        _PACER.wait()
        return find_instrument(isin)

    def recognize(self, binding: EnricherBinding) -> EnricherRecognition:
        isin = _isin(binding)
        if isin is None:
            return EnricherRecognition(found=False)
        try:
            instrument = self._find(isin)
        except RateLimited as error:
            raise AssetRateLimitedError(f"The ESMA register refused for too many requests: {error}", retry_after=getattr(error, "retry_after", None)) from error
        if instrument is None:
            return EnricherRecognition(found=False)
        return EnricherRecognition(found=True, name=instrument.full_name, page_url=None, identifiers={"LEI": instrument.issuer_lei} if instrument.issuer_lei else {})

    def read(self, bindings: list[EnricherBinding], keys: Iterable[str] | None = None) -> Iterator[EnricherReadItem]:
        refused = False
        for index, binding in enumerate(bindings):
            isin = _isin(binding)
            if isin is None:
                yield EnricherReadItem(index=index, status=EnricherReadStatus.NOT_FOUND)
                continue
            if refused:
                yield EnricherReadItem(index=index, status=EnricherReadStatus.ERROR, error_code=RATE_LIMITED)
                continue
            try:
                instrument = self._find(isin)
            except RateLimited as error:
                refused = True
                logger.warning("The ESMA register refused for too many requests", isin=isin, retry_after=getattr(error, "retry_after", None))
                yield EnricherReadItem(index=index, status=EnricherReadStatus.ERROR, error_code=RATE_LIMITED, retry_after=getattr(error, "retry_after", None))
                continue
            except Exception as error:  # noqa: BLE001 — isolation boundary: one instrument's failure is that instrument's outcome
                logger.warning("ESMA register read failed", isin=isin, exc_info=error)
                yield EnricherReadItem(index=index, status=EnricherReadStatus.ERROR, error_code=SOURCE_ERROR, error_message=type(error).__name__)
                continue
            if instrument is None:
                yield EnricherReadItem(index=index, status=EnricherReadStatus.NOT_FOUND)
                continue
            yield EnricherReadItem(index=index, status=EnricherReadStatus.OK, values=instrument_voices(instrument))
