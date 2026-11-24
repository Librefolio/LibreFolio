"""The test enricher (plan 68, B1): fixed answers from the identifier alone, no network, test mode only.

What it answers, so the tests of the core can drive it:

- ``recognize``: a binding whose identifier starts with ``UNKNOWN_PREFIX`` is not found; any other is found, named
  ``Mock <identifier>``, and an ISIN also brings the LEI ``lei_of(isin)``;
- ``read``: an identifier equal to ``NOT_FOUND_IDENTIFIER`` is not found, ``ERROR_IDENTIFIER`` fails,
  ``RATE_LIMITED_IDENTIFIER`` is refused for too many requests (``retry_after`` ``RATE_LIMITED_RETRY_AFTER``); any
  other gives ``READ_VALUES`` plus its own description, with ``SOURCE_DATE``;
- ``search`` (ENR-3): a text starting with ``UNKNOWN_PREFIX`` finds nothing; any other finds one result, ``Mock
  <text>``, bound by ISIN when the text has an ISIN's form (``ISIN_FORM``, no check digit: the tests' ISINs are made
  up), else by TICKER, upper case; no parameters (the mock declares none).
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator
from datetime import date

from backend.app.db.models import AssetType
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
from backend.app.services.platform.provider_registry import register_provider

UNKNOWN_PREFIX = "UNKNOWN"
#: The form of an ISIN, without the check digit: the tests make theirs up.
ISIN_FORM = re.compile(r"[A-Z]{2}[A-Z0-9]{9}[0-9]")
NOT_FOUND_IDENTIFIER = "MOCK_NOT_FOUND"
ERROR_IDENTIFIER = "MOCK_ERROR"
RATE_LIMITED_IDENTIFIER = "MOCK_RATE_LIMITED"
RATE_LIMITED_RETRY_AFTER = 30.0
SOURCE_DATE = date(2026, 9, 30)
#: The voices every successful read gives, as raw values.
READ_VALUES = {"ter": "0.0022", "geography": {"USA": "0.6", "JPN": "0.4"}, "distribution_policy": "accumulating"}

_FUND_VOICES = frozenset({"ter", "fund_size", "replication", "distribution_policy", "geography", "sector", "description"})
_STOCK_VOICES = frozenset({"sector", "industry", "issuer_country", "market_cap", "description"})
_BOND_VOICES = frozenset({"coupon_rate", "maturity_date", "issuer_name", "issuer_lei", "yield_gross", "description"})
_NOT_COVERED = frozenset({AssetType.INDEX, AssetType.HOLD, AssetType.CROWDFUND, AssetType.CROWDFUND_REAL_ESTATE})


def lei_of(isin: str) -> str:
    """The LEI the mock knows for an ISIN: 20 characters, the same every time."""
    return f"MOCKLEI{isin[-13:]:0>13}"[:20]


def _voices() -> dict[AssetType, frozenset[str]]:
    voices: dict[AssetType, frozenset[str]] = {}
    for asset_type in AssetType:
        if asset_type in _NOT_COVERED:
            continue
        if asset_type in (AssetType.ETF, AssetType.FUND) or asset_type.value.startswith("ETF_"):
            voices[asset_type] = _FUND_VOICES
        elif asset_type == AssetType.BOND:
            voices[asset_type] = _BOND_VOICES
        else:
            voices[asset_type] = _STOCK_VOICES
    return voices


@register_provider(EnricherRegistry)
class MockEnricher(EnricherPlugin):
    """Fixed answers for the tests of the enricher core."""

    code = "mockenrich"
    name = "Mock enricher"
    terms = EnricherTerms.OPEN
    test_only = True
    calls_external_service = False
    accepted_identifier_types = ("ISIN", "LEI", "TICKER")
    voices = _voices()
    default_priority = {asset_type: None if asset_type in _NOT_COVERED else 100 for asset_type in AssetType}

    def recognize(self, binding: EnricherBinding) -> EnricherRecognition:
        if binding.identifier.startswith(UNKNOWN_PREFIX):
            return EnricherRecognition(found=False)
        identifiers = {"LEI": lei_of(binding.identifier)} if binding.identifier_type == "ISIN" else {}
        return EnricherRecognition(found=True, name=f"Mock {binding.identifier}", page_url=self.page_url(binding), identifiers=identifiers)

    def read(self, bindings: list[EnricherBinding], keys: Iterable[str] | None = None) -> Iterator[EnricherReadItem]:
        for index, binding in enumerate(bindings):
            if binding.identifier == NOT_FOUND_IDENTIFIER:
                yield EnricherReadItem(index=index, status=EnricherReadStatus.NOT_FOUND)
            elif binding.identifier == ERROR_IDENTIFIER:
                yield EnricherReadItem(index=index, status=EnricherReadStatus.ERROR, error_code="MOCK_ERROR", error_message="the mock fails on purpose")
            elif binding.identifier == RATE_LIMITED_IDENTIFIER:
                yield EnricherReadItem(index=index, status=EnricherReadStatus.ERROR, error_code=RATE_LIMITED, retry_after=RATE_LIMITED_RETRY_AFTER)
            else:
                values = {**READ_VALUES, "description": f"Mock description of {binding.identifier}"}
                yield EnricherReadItem(index=index, status=EnricherReadStatus.OK, values=values, source_date=SOURCE_DATE)

    def search(self, query: str) -> list[EnricherSearchResult]:
        text = query.strip()
        if not text or text.upper().startswith(UNKNOWN_PREFIX):
            return []
        upper = text.upper()
        binding = EnricherBinding(identifier_type="ISIN" if ISIN_FORM.fullmatch(upper) else "TICKER", identifier=upper)
        return [EnricherSearchResult(name=f"Mock {text}", binding=binding, page_url=self.page_url(binding), market="MOCK")]

    def page_url(self, binding: EnricherBinding) -> str | None:
        return f"https://mockenrich.invalid/{binding.identifier}"

    @property
    def test_cases(self) -> list[dict]:
        return []
