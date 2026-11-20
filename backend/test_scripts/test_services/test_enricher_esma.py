"""
The ESMA enricher (plan 68, lot C4b): ``enricher_providers/esma/plugin.py``, class ``EsmaEnricher``, on our library
``esma-registers`` (FIRDS, the register of financial instruments, by ISIN).

What it promises, pinned here with no network:
1. **Declarations**: ``code`` ``esma``, ``terms`` ``OPEN`` (an official register, the source cited), ``ISIN`` only, no
   ``params_schema``, no search, not test-only. Degree 30 (after the sources of each type) for ``STOCK``, ``BOND``,
   ``FUND``, ``COMMODITY`` and the ETF family (``ETF`` and every ``ETF_*``); ``None`` for every other type. One
   module-level ``Pacer`` spaces every call to the register (the tests run it on a fake clock: no test waits).
2. **Mapping**, from the CFI code (ISO 10962) and the register's fields, every value in the catalogue's stored form:
   - every instrument: ``issuer_lei``;
   - ``legal_form``: ``ES…`` a share, ``DB…`` a bond, ``EY…`` an ETC or ETN (the research's table); a fund's ``C…``
     says nothing of UCITS, so no legal form;
   - a bond (``DB``): ``maturity_date``; ``coupon_type`` from the type of interest (``F`` fixed, ``V`` floating, ``Z``
     zero coupon); ``coupon_rate`` only for a fixed rate, as a fraction (for BTP Italia and BTP Valore, ``DBV``, the
     register's «fixed rate» is the coupon of one period: never written); ``issuer_type`` from the guarantee (``T`` the
     State, ``C`` supranational), absent for any other letter;
   - a fund (``CE``, ``CI``): ``distribution_policy`` from its policy letter (``G`` accumulating, ``I`` distributing;
     ``J`` mixed, absent).
3. **Not found**: an ISIN the register does not have; a binding that is not an ISIN, or not a valid one, with no call.
4. **recognize**: found → the register's full name, the LEI as an identifier for the cascade (B4), no page; a refusal
   for too many requests raises an ``AssetRateLimitedError`` with the register's ``retry_after``.
5. **read**: one item per binding with its index; a refusal → ``RATE_LIMITED`` with its ``retry_after`` for that binding
   and ``RATE_LIMITED`` for every later one, without a call; another failure → ``SOURCE_ERROR``, isolated.

No network, by construction: the plugin module's ``find_instrument`` is replaced by the library's real one on a fake
transport that answers the recorded bodies (``fixtures/esma_enricher/``, recorded by the library's own
``tools/record_fixtures.py``) for the ISINs a test offers, and fails the test (``pytest.fail``) for any other.
"""

from __future__ import annotations

import importlib
import json
import threading
from pathlib import Path

import esma_registers
import httpx
import pytest
from esma_registers import RateLimited, RegisterUnavailable

from backend.app.db.models import AssetType
from backend.app.services.assets.base import AssetRateLimitedError, rate_limited_from_exception
from backend.app.services.assets.profile.catalogue import normalize_value
from backend.app.services.enrichers.base import RATE_LIMITED, EnricherBinding, EnricherReadStatus, EnricherTerms
from backend.app.utils.runtime.pacing import Pacer

PLUGIN_MODULE = "backend.app.services.enricher_providers.esma.plugin"
CODE = "esma"
FIXTURES = Path(__file__).parent / "fixtures" / "esma_enricher"
RECORDINGS = {
    "enel": "IT0003128367",
    "btp_italia": "IT0005648255",
    "btp_2072": "IT0005441883",
    "bond_corp": "XS2331921390",
    "swda": "IE00B4L5Y983",
    "etc_gold": "IE00B4ND3602",
    "not_found_fund": "IT0005487001",
}
ETF_FAMILY = {asset_type for asset_type in AssetType if asset_type == AssetType.ETF or asset_type.value.startswith("ETF_")}
COVERED = {AssetType.STOCK, AssetType.BOND, AssetType.FUND, AssetType.COMMODITY} | ETF_FAMILY


@pytest.fixture
def esma():
    return importlib.import_module(PLUGIN_MODULE)


class Register:
    """The plugin's ``find_instrument``: the library's real one, answered by the recorded bodies of the ISINs offered."""

    def __init__(self) -> None:
        self._real = esma_registers.find_instrument
        self.bodies: dict[str, dict] = {}
        self.failures: dict[str, Exception] = {}
        self.calls: list[str] = []

    def offer(self, name: str) -> str:
        isin = RECORDINGS[name]
        self.bodies[isin] = json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))
        return isin

    def fail(self, isin: str, error: Exception) -> str:
        self.failures[isin] = error
        return isin

    def __call__(self, isin: str, **kwargs):
        self.calls.append(isin)
        if isin in self.failures:
            raise self.failures[isin]
        if isin not in self.bodies:
            pytest.fail(f"the plugin asked the register for {isin!r}, which no test offered")
        body = self.bodies[isin]
        with httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, json=body))) as client:
            return self._real(isin, client=client)


@pytest.fixture
def register(esma, monkeypatch: pytest.MonkeyPatch) -> Register:
    fake = Register()
    monkeypatch.setattr(esma, "find_instrument", fake, raising=True)
    return fake


class FakePace:
    """The module's ``_PACER`` on a fake clock that only moves when it sleeps: no test waits, and the waits are kept."""

    def __init__(self) -> None:
        self.now = 1000.0
        self.slept: list[float] = []
        self._lock = threading.Lock()

    def clock(self) -> float:
        with self._lock:
            return self.now

    def sleep(self, seconds: float) -> None:
        with self._lock:
            self.slept.append(seconds)
            self.now += seconds


@pytest.fixture(autouse=True)
def pace(monkeypatch: pytest.MonkeyPatch) -> FakePace:
    module = importlib.import_module(PLUGIN_MODULE)
    real = module._PACER
    assert isinstance(real, Pacer) and real.interval_seconds > 0, "the plugin paces its calls with a module-level Pacer"
    fake = FakePace()
    monkeypatch.setattr(module, "_PACER", Pacer(real.interval_seconds, clock=fake.clock, sleep=fake.sleep), raising=True)
    return fake


def binding(isin: str, identifier_type: str = "ISIN") -> EnricherBinding:
    return EnricherBinding(identifier_type=identifier_type, identifier=isin)


def read_one(esma, isin: str):
    [item] = list(esma.EsmaEnricher().read([binding(isin)]))
    return item


def values_of(esma, register: Register, name: str) -> dict:
    item = read_one(esma, register.offer(name))
    assert item.status is EnricherReadStatus.OK, item
    for key, value in item.values.items():
        assert normalize_value(key, value) == value, f"{key} is in the catalogue's stored form: {value!r}"
    return item.values


# =============================================================================
# 1. Declarations
# =============================================================================


def test_declarations(esma):
    plugin = esma.EsmaEnricher()
    assert plugin.code == CODE
    assert plugin.terms is EnricherTerms.OPEN
    assert tuple(plugin.accepted_identifier_types) == ("ISIN",)
    assert plugin.params_schema in ([], None) or not plugin.params_schema
    assert plugin.supports_search is False
    assert getattr(plugin, "test_only", False) is False
    assert plugin.help_url and "registers.esma.europa.eu" in plugin.help_url
    assert {asset_type for asset_type, degree in plugin.default_priority.items() if degree is not None} == COVERED
    assert set(plugin.default_priority) == set(AssetType), "a degree for every type, None written out"
    assert all(degree == 30 for degree in plugin.default_priority.values() if degree is not None), "after the sources of each type"
    assert set(plugin.voices) == COVERED
    assert plugin.voices[AssetType.STOCK] == {"issuer_lei", "legal_form"}
    assert plugin.voices[AssetType.BOND] == {"issuer_lei", "legal_form", "maturity_date", "coupon_type", "coupon_rate", "issuer_type"}
    assert plugin.voices[AssetType.FUND] == plugin.voices[AssetType.ETF] == {"issuer_lei", "distribution_policy"}
    assert plugin.voices[AssetType.COMMODITY] == {"issuer_lei", "legal_form"}
    assert plugin.page_url(binding(RECORDINGS["enel"])) is None, "the register has no page per instrument"
    assert [case["binding"]["identifier_type"] for case in plugin.test_cases] and all(case["binding"]["identifier_type"] == "ISIN" for case in plugin.test_cases)


# =============================================================================
# 2. Mapping, on the recorded answers
# =============================================================================


def test_a_share(esma, register):
    assert values_of(esma, register, "enel") == {"issuer_lei": "WOCMU6HCI0OJWNPRZS33", "legal_form": "share"}


def test_a_fixed_rate_state_bond(esma, register):
    assert values_of(esma, register, "btp_2072") == {
        "issuer_lei": "815600DE60799F5A9309",
        "legal_form": "bond",
        "issuer_type": "sovereign",
        "coupon_type": "fixed",
        "coupon_rate": "0.0215",
        "maturity_date": "2072-03-01",
    }


def test_a_variable_rate_state_bond_never_takes_the_period_coupon_for_the_yearly_rate(esma, register):
    values = values_of(esma, register, "btp_italia")
    assert values == {"issuer_lei": "815600DE60799F5A9309", "legal_form": "bond", "issuer_type": "sovereign", "coupon_type": "floating", "maturity_date": "2032-06-04"}
    assert "coupon_rate" not in values, "the register's 0.925 is the coupon of one period"


def test_a_senior_corporate_bond_has_no_issuer_type_from_the_cfi(esma, register):
    values = values_of(esma, register, "bond_corp")
    assert values == {"issuer_lei": "549300T1EREIRH8ICX03", "legal_form": "bond", "coupon_type": "fixed", "coupon_rate": "0.015", "maturity_date": "2028-04-22"}


def test_an_accumulating_etf_has_no_legal_form(esma, register):
    assert values_of(esma, register, "swda") == {"issuer_lei": "549300QS4Q1IT6XCA514", "distribution_policy": "accumulating"}


def test_an_etc(esma, register):
    assert values_of(esma, register, "etc_gold") == {"issuer_lei": "549300T2ISPWHQ8IPF83", "legal_form": "etc_etn"}


@pytest.mark.parametrize(
    ("cfi", "expected"),
    [
        ("CIOIES", {"distribution_policy": "distributing"}),
        ("CEOJES", {}),
        ("DBZUFB", {"legal_form": "bond", "coupon_type": "zero_coupon"}),
        ("DBFCFB", {"legal_form": "bond", "issuer_type": "supranational", "coupon_type": "fixed"}),
        ("DBKTFB", {"legal_form": "bond", "issuer_type": "sovereign"}),
        ("ESXXXX", {"legal_form": "share"}),
        ("RWXXXX", {}),
        ("", {}),
    ],
)
def test_the_cfi_letters(esma, cfi, expected):
    """The table on its own (synthetic codes: the recordings hold one of each kind)."""
    assert esma.cfi_voices(cfi) == expected


# =============================================================================
# 3. Not found
# =============================================================================


def test_an_isin_the_register_does_not_have(esma, register):
    item = read_one(esma, register.offer("not_found_fund"))
    assert item.status is EnricherReadStatus.NOT_FOUND


@pytest.mark.parametrize(("identifier", "identifier_type"), [("ENEL.MI", "TICKER"), ("IT0003128368", "ISIN"), ("not an isin", "ISIN")])
def test_a_binding_that_is_not_a_valid_isin_asks_nothing(esma, register, identifier, identifier_type):
    [item] = list(esma.EsmaEnricher().read([binding(identifier, identifier_type)]))
    assert item.status is EnricherReadStatus.NOT_FOUND
    assert register.calls == []


# =============================================================================
# 4. recognize
# =============================================================================


def test_recognize_gives_the_name_and_the_lei(esma, register):
    recognition = esma.EsmaEnricher().recognize(binding(register.offer("btp_2072")))
    assert recognition.found is True
    assert recognition.name == "BTPS 2.150 01/03/72"
    assert recognition.identifiers == {"LEI": "815600DE60799F5A9309"}
    assert recognition.page_url is None


def test_recognize_not_found_and_not_an_isin(esma, register):
    assert esma.EsmaEnricher().recognize(binding(register.offer("not_found_fund"))).found is False
    assert esma.EsmaEnricher().recognize(binding("ENEL.MI", "TICKER")).found is False
    assert register.calls == [RECORDINGS["not_found_fund"]]


def test_recognize_raises_a_refusal_with_its_wait(esma, register):
    isin = register.fail(RECORDINGS["enel"], RateLimited("too many", retry_after=7.0))
    with pytest.raises(AssetRateLimitedError) as raised:
        esma.EsmaEnricher().recognize(binding(isin))
    assert raised.value.retry_after == 7.0
    assert rate_limited_from_exception(raised.value, CODE) is raised.value


# =============================================================================
# 5. read
# =============================================================================


def test_read_isolates_a_failure_and_stops_after_a_refusal(esma, register):
    broken = register.fail("FR0000120271", RegisterUnavailable("down", status=503))
    ok = register.offer("enel")
    refused = register.fail(RECORDINGS["swda"], RateLimited("too many", retry_after=12.0))
    later = register.offer("btp_2072")
    items = list(esma.EsmaEnricher().read([binding(broken), binding(ok), binding(refused), binding(later)]))

    assert [item.index for item in items] == [0, 1, 2, 3]
    assert (items[0].status, items[0].error_code) == (EnricherReadStatus.ERROR, esma.SOURCE_ERROR)
    assert items[1].status is EnricherReadStatus.OK
    assert (items[2].status, items[2].error_code, items[2].retry_after) == (EnricherReadStatus.ERROR, RATE_LIMITED, 12.0)
    assert (items[3].status, items[3].error_code) == (EnricherReadStatus.ERROR, RATE_LIMITED)
    assert later not in register.calls, "after a refusal no more calls"


def test_two_reads_share_one_pace(esma, register, pace):
    first, second = register.offer("enel"), register.offer("btp_2072")
    list(esma.EsmaEnricher().read([binding(first)]))
    list(esma.EsmaEnricher().read([binding(second)]))
    assert pace.slept and pace.slept[-1] > 0, "the second read waited the plugin's interval"
