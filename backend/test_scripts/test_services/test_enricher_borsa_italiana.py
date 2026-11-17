"""
The Borsa Italiana enricher (plan 68, lot C2): ``enricher_providers/borsa_italiana/plugin.py``, class
``BorsaItalianaEnricher``. Bonds first, and the sector of a stock; funds are not in this lot.

What it promises, pinned here with no network:

1. **Declarations**: ``code`` ``borsa_italiana``, ``name`` ``Borsa Italiana``, ``terms`` ``PRICE_SOURCE``, ISIN only, not
   test-only. ``BOND`` at degree 10, ``STOCK`` at degree 20 (Yahoo, a later lot, leads stocks), every other type ``None``
   (``CRYPTO`` among them: the recognize API test without ``codes`` relies on it). Twenty bond voices, never
   ``inception_date`` (correction C2-fix-1); ``sector`` and
   ``legal_form`` for a stock. Binding params ``language`` (select ``en``/``it``, default ``en``, not required), ``mic``
   and ``platform`` (strings, not required), each with an ``x-i18n-key`` under ``enrichers.borsa_italiana.`` (the texts are
   the implementer's: only keys and defaults are pinned). ``test_cases`` for the external suite. No import from the price
   plugin of the same name (``asset_source_providers/``).

2. **Mapping** of the recorded sheets (``fixtures/borsa_italiana_enricher/``, the library's ``SchedaStrumento`` rebuilt
   with its real field types), every yielded value passed through the real catalogue (``normalize_value``) and compared
   in its **stored** form:

   - a bond (``tipo == "obbligazione"``): percents become fractions (``/100``, exact): coupon, period coupon, gross and
     net yield; the modified duration (years) and the accrued interest (per 100 nominal) are not percents. A missing
     annual coupon is the period coupon times the coupons per year (``financial_math.interest.annual_coupon_rate``):
     ``btp_ord`` 3.00 semiannual → 0.06, ``btp_2072`` 1.075 → 0.0215; where the sheet gives both, they agree. The texts of
     the page are translated by the plugin's own tables, in either language: frequency, structure («Plain Vanilla» says
     no special structure: absent, with no log line), day count, issuer type; an unknown text leaves its voice out with
     one log line. A sovereign issuer gives its country and a geography of one country at 100 %, through the plugin's
     own table of issuers; any other issuer gives neither. The sector is «Government Bonds» for a sovereign issuer,
     «Corporate Bonds» for a corporate one. ``legal_form`` ``bond``. Never the page's advertising ``descrizione``.
     Never ``inception_date`` (correction C2-fix-1): the page's ``data_primo_giorno`` is a venue's first day of
     trading, not a launch date (BTP 6 % 2031 shows 2008-11-03 on an ISIN of the late-90s series). The outstanding
     amount is in ``valuta_denominazione`` when the page gives it, else in ``valuta`` (correction C2-fix-2); both given
     and different: no outstanding amount, one log line naming both currencies. No bond recording gives
     ``valuta_denominazione`` (only the ETF ``swda`` does), so their stored forms are unchanged by it;
   - a stock (``tipo == "azione"``): ``sector`` (one sector at 100 %) when the sheet gives one the generic helper
     (``utils/asset/sector.py``) knows, passed on as it is; a name it does not know leaves ``sector`` out with one log
     line, never «Other» at 100 % (correction C2b-2); ``legal_form`` ``share``, nothing else;
   - any other ``tipo`` (an ETF): found, OK, no values;
   - **per-voice dates**: yields, modified duration and accrued interest are «as of» the reference price date, given in
     ``source_dates`` for those of the four the item gives; nothing else is dated, the item's ``source_date`` stays None;
   - **language**: the binding's ``language`` is the page asked (``lingua``). For each MOT bond the English and the
     Italian page give the same stored values but for ``payout_description``, a text in the page's language. The EuroTLX
     bond (``bond_corp``) does not: each page is pinned as it is.

3. **recognize**: non-ISIN → not found, no call; otherwise one ``ottieni_scheda`` with the binding's ``mic``,
   ``language`` and ``platform``; the sheet's name and page; ``StrumentoNonTrovato`` / ``StrumentoNonRisolto`` → not
   found; ``RateLimitRaggiunto`` (the library's refusal, an HTTP 403 from the site's firewall, no «429» in its text) →
   an exception ``rate_limited_from_exception`` recognises; any other error raises.

4. **read**: one item per binding, keyed by ``index``; non-ISIN → ``NOT_FOUND`` with no call; not found → ``NOT_FOUND``;
   ``RateLimitRaggiunto`` → ``ERROR`` ``RATE_LIMITED`` and every binding after it the same, without a call; another
   error → ``ERROR`` ``SOURCE_ERROR``, the next binding still read. One library ``Sessione`` per ``read``, handed to
   every call of that read (the library paces its own requests), and closed exactly once (``chiudi``, or the context
   manager's exit): after a normal read, after a failing binding or a refusal, and when the consumer closes the
   generator early (correction C2b-1).

5. **search**: ``cerca(query, lingua="it", sessione=…)``, the session closed exactly once, also when ``cerca``
   raises (correction C2b-1; recognize's session is the library's own, unpinned); one result per hit, bound by ISIN with the hit's ``mic``,
   ``BOND`` for a bond, ``STOCK`` for a share, ``None`` otherwise, with the plugin's page of that binding.

6. **page_url**: ``https://www.borsaitaliana.it/borsa/search/scheda.html?code=<ISIN>&lang=<language>``, then
   ``&mic=…`` and ``&platform=…`` when the binding has them (the price plugin's form).

No network, by construction: the plugin module is imported in a fixture, which replaces ``ottieni_scheda``, ``cerca`` and
``Sessione`` on it (``raising=True``: the names must be imported at module level into the plugin) with fakes. The fake
library answers only the ``(isin, lingua)`` pairs a test offered and fails the test (``pytest.fail``, a
``BaseException`` no plugin ``except Exception`` swallows) for any other call; the fake session fails on any request.
Assumed: the plugin keeps no sheet cache of its own (the read cache is the core's), so the call logs are exact.

Kept in one section, «Language», the tests of the ``language`` binding param: its placement may move to an instance
setting after the consultant's answer.

Red before C2: the plugin module does not exist; every test fails on its own at the fixture's import
(``ModuleNotFoundError``), nothing at collection. The cross-check of the annual coupon also needs
``financial_math.interest.annual_coupon_rate`` (``test_financial_math/test_annual_coupon_rate.py``).

PURE: no database, no server, no network.
"""

from __future__ import annotations

import ast
import contextlib
import copy
import dataclasses
import importlib
import importlib.util
import json
import typing
from collections.abc import Iterator
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import ModuleType
from typing import Any

import borsa_italiana_scraping as bis
import pytest
from structlog.testing import capture_logs

from backend.app.config import is_test_mode
from backend.app.db.models import AssetType
from backend.app.services.assets.base import rate_limited_from_exception
from backend.app.services.assets.profile.catalogue import CATALOGUE, normalize_value
from backend.app.services.enrichers.base import (
    RATE_LIMITED,
    EnricherBinding,
    EnricherReadItem,
    EnricherReadStatus,
    EnricherRecognition,
    EnricherSearchResult,
    EnricherTerms,
)
from backend.app.services.enrichers.registry import EnricherRegistry
from backend.app.utils.asset.sector import validate_sector

PLUGIN_MODULE = "backend.app.services.enricher_providers.borsa_italiana.plugin"
CODE = "borsa_italiana"
TEST_MODE_VARIABLE = "LIBREFOLIO_TEST_MODE"
FIXTURES = Path(__file__).parent / "fixtures" / "borsa_italiana_enricher"
SOURCE_ERROR = "SOURCE_ERROR"
I18N_PREFIX = f"enrichers.{CODE}."

BOND_VOICES = frozenset(
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
        "geography",
        "sector",
        "legal_form",
    }
)
STOCK_VOICES = frozenset({"sector", "legal_form"})
COVERED = {AssetType.BOND: 10, AssetType.STOCK: 20}
#: The voices «as of» the reference price date.
AS_OF_VOICES = frozenset({"yield_gross", "yield_net", "modified_duration", "accrued_interest"})
#: The reference price date of every bond recording (2026-11-09).
REFERENCE_DATE = date(2026, 11, 9)
#: The MOT bonds: English and Italian pages agree on every stored value but the payout text.
MOT_BONDS = ("btp_valore", "btp_ord", "btp_italia", "btp_2072", "austria_2117")
BONDS = (*MOT_BONDS, "bond_corp")
LANGUAGES = ("en", "it")
#: The library's own refusal for too many requests: an HTTP 403 from the site's firewall (``sessione.py``), no «429».
WAF_MESSAGE = "HTTP 403 — accesso bloccato dal WAF (url=https://www.borsaitaliana.it/borsa/search/scheda.html)"


# =============================================================================
# Expected stored forms (written out from the catalogue, never recomputed with the plugin's own logic)
# =============================================================================

GOVERNMENT = {"Government Bonds": "1.0000"}
CORPORATE = {"Corporate Bonds": "1.0000"}


def _italian_bond(**fields: Any) -> dict[str, Any]:
    return {"issuer_name": "REPUBLIC OF ITALY", "issuer_type": "sovereign", "issuer_country": "ITA", "geography": {"ITA": "1.0000"}, "sector": GOVERNMENT, **_listed(**fields)}


def _listed(**fields: Any) -> dict[str, Any]:
    return {"legal_form": "bond", "min_lot": "1000", "reference_price_date": "2026-11-09", "day_count": "act_act_icma", **fields}


#: Per bond recording, the English page: every voice in stored form but ``payout_description`` (compared with the
#: recording's own text when it has one).
EXPECTED_BONDS_EN: dict[str, dict[str, Any]] = {
    # step-up: «Structured Interest Rate»; quarterly 1.125 and annual 4.50 both given
    "btp_valore": _italian_bond(
        maturity_date="2028-10-10",
        coupon_rate="0.045",
        coupon_period_rate="0.01125",
        coupon_frequency="quarterly",
        coupon_type="structured",
        yield_gross="0.0361",
        yield_net="0.0304",
        modified_duration="1.78",
        accrued_interest="0.3913",
        outstanding_amount={"amount": "17190004000", "currency": "EUR"},
    ),
    # an ordinary BTP: no annual coupon on the page, 3.00 semiannual → 6 %; «Plain Vanilla» → no coupon type
    "btp_ord": _italian_bond(
        maturity_date="2031-05-01",
        coupon_rate="0.06",
        coupon_period_rate="0.03",
        coupon_frequency="semiannual",
        yield_gross="0.0369",
        yield_net="0.0297",
        modified_duration="3.87",
        accrued_interest="0.16575",
        outstanding_amount={"amount": "30762750000", "currency": "EUR"},
    ),
    "btp_italia": _italian_bond(
        maturity_date="2032-06-04",
        coupon_rate="0.0185",
        coupon_period_rate="0.00925",
        coupon_frequency="semiannual",
        coupon_type="inflation_linked",
        yield_gross="0.0524",
        yield_net="0.0445",
        modified_duration="3.35",
        accrued_interest="0.80874",
        outstanding_amount={"amount": "2257423000", "currency": "EUR"},
    ),
    # no annual coupon on the page: 1.075 semiannual → 2.15 %, the rate of its name «Btp Tf 2,15% Mz72»
    "btp_2072": _italian_bond(
        maturity_date="2072-03-01",
        coupon_rate="0.0215",
        coupon_period_rate="0.01075",
        coupon_frequency="semiannual",
        yield_gross="0.045",
        yield_net="0.0407",
        modified_duration="21.94",
        accrued_interest="0.42169",
        outstanding_amount={"amount": "6900000000", "currency": "EUR"},
    ),
    "austria_2117": {
        "issuer_name": "REPUBLIC OF AUSTRIA",
        "issuer_type": "sovereign",
        "issuer_country": "AUT",
        "geography": {"AUT": "1.0000"},
        "sector": GOVERNMENT,
        **_listed(
            maturity_date="2117-09-20",
            coupon_rate="0.021",
            coupon_period_rate="0.021",
            coupon_frequency="annual",
            yield_gross="0.0365",
            yield_net="0.0324",
            modified_duration="27.9",
            accrued_interest="0.29918",
            outstanding_amount={"amount": "3500000000", "currency": "EUR"},
        ),
    },
    # EuroTLX, English page: «12 Months» (annual), no period coupon, no structure, no day count, no tipologia (so no
    # issuer type and no sector), a company issuer (no country), no outstanding amount
    "bond_corp": {
        "maturity_date": "2028-04-22",
        "coupon_rate": "0.015",
        "coupon_frequency": "annual",
        "yield_gross": "0.0376",
        "yield_net": "0.0334",
        "modified_duration": "1.38",
        "accrued_interest": "0.83425",
        "issuer_name": "Anima Holding S.P.A.",
        "legal_form": "bond",
        "min_lot": "100000",
        "reference_price_date": "2026-11-09",
    },
}

#: EuroTLX, Italian page: no coupon frequency at all; «Obbligazioni Finanziarie» → a corporate issuer.
EXPECTED_BOND_CORP_IT = {
    **{key: value for key, value in EXPECTED_BONDS_EN["bond_corp"].items() if key != "coupon_frequency"},
    "issuer_type": "corporate",
    "sector": CORPORATE,
}

#: The stocks and an ETF, English pages.
EXPECTED_OTHERS: dict[str, dict[str, Any]] = {
    "enel": {"sector": {"Utilities": "1.0000"}, "legal_form": "share"},
    "asml": {"sector": {"Technology": "1.0000"}, "legal_form": "share"},
    # Global Equity Market: no sector on the page
    "apple": {"legal_form": "share"},
    # an ETF: found, nothing for this lot
    "swda": {},
}


# =============================================================================
# The recordings, rebuilt as the library returns them
# =============================================================================

_FIELDS = tuple(field.name for field in dataclasses.fields(bis.SchedaStrumento))
_HINTS = typing.get_type_hints(bis.SchedaStrumento)


def _recording(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


def _call(name: str, language: str) -> dict[str, Any]:
    return _recording(name)["calls"][f"scheda_{language}"]


def _typed(field: str, value: Any) -> Any:
    """A recorded JSON value as the library's field type: text → ``Decimal`` or ``date``, never a plain string."""
    if value is None:
        return None
    hint = _HINTS[field]
    kinds = set(typing.get_args(hint)) - {type(None)} or {hint}
    if Decimal in kinds:
        assert isinstance(value, str), f"{field}: a recorded decimal is text, got {value!r}"
        return Decimal(value)
    if date in kinds:
        return date.fromisoformat(value)
    if int in kinds:
        assert type(value) is int, f"{field}: an int, got {value!r}"
        return value
    if str in kinds:
        assert isinstance(value, str), f"{field}: a text, got {value!r}"
        return value
    if any(typing.get_origin(kind) is list for kind in kinds):
        assert isinstance(value, list) and all(isinstance(item, str) for item in value), f"{field}: a list of texts, got {value!r}"
        return list(value)
    raise AssertionError(f"{field}: no rule for the type {hint!r}")


def _sheet(name: str, language: str = "en") -> bis.SchedaStrumento:
    """The recorded ``SchedaStrumento`` of ``name`` in ``language``, with the library's real types."""
    response = _call(name, language)["response"]
    assert response is not None, f"barrier: {name} {language} recorded a sheet"
    assert set(response) == set(_FIELDS), f"{name}: the recording does not match the installed library: {sorted(set(response) ^ set(_FIELDS))}"
    return bis.SchedaStrumento(**{field: _typed(field, response[field]) for field in _FIELDS})


def _recorded_error(name: str, language: str = "en") -> BaseException:
    """The recorded error of ``name`` («Class: message») as the library's own exception."""
    text = _call(name, language)["error"]
    assert text, f"barrier: {name} {language} recorded an error"
    class_name, _, message = text.partition(": ")
    error_class = getattr(bis, class_name)
    assert issubclass(error_class, bis.BorsaItalianaErrore), f"barrier: {class_name} is the library's error"
    return error_class(message)


# =============================================================================
# The fake library, the fake session and the plugin
# =============================================================================


class FakeSession:
    """Stands for ``borsa_italiana_scraping.Sessione``, with its closing API only (``chiudi``, and the context manager
    whose exit calls ``chiudi``, as the library's does): counts its closes, fails the test on any request."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.closes = 0

    def chiudi(self) -> None:
        self.closes += 1

    def __enter__(self) -> FakeSession:
        return self

    def __exit__(self, *exc: object) -> None:
        self.chiudi()

    def __getattr__(self, name: str) -> Any:
        if name.startswith("__"):
            raise AttributeError(name)
        pytest.fail(f"Sessione.{name} used: a real request to borsaitaliana.it")


class FakeLibrary:
    """``ottieni_scheda`` answering only the ``(isin, lingua)`` pairs a test offered (a sheet, or an exception to raise),
    ``cerca`` only the queries offered, each with a log of its calls; anything else fails the test."""

    def __init__(self) -> None:
        self.sheets: dict[tuple[str, str], Any] = {}
        self.calls: list[tuple[str, str | None, str, str | None]] = []
        self.call_sessions: list[Any] = []
        self.answers: dict[str, list[bis.RisultatoRicerca]] = {}
        self.search_calls: list[tuple[str, str]] = []
        self.sessions: list[FakeSession] = []

    def give(self, isin: str, answer: Any, language: str = "en") -> str:
        self.sheets[(isin, language)] = answer
        return isin

    def ottieni_scheda(self, isin: str, mic: str | None = None, lingua: str = "en", sessione: Any = None, platform: str | None = None, url_diretto: str | None = None) -> bis.SchedaStrumento:
        self.calls.append((isin, mic, lingua, platform))
        self.call_sessions.append(sessione)
        if isinstance(sessione, FakeSession) and sessione.closes:
            pytest.fail(f"ottieni_scheda called for {isin!r} on a session already closed")
        if (isin, lingua) not in self.sheets:
            pytest.fail(f"ottieni_scheda called for {(isin, lingua)!r}, which this test never offered (a call the contract forbids, or a fetch from borsaitaliana.it)")
        answer = self.sheets[(isin, lingua)]
        if isinstance(answer, BaseException):
            raise answer
        return copy.deepcopy(answer)

    def cerca(self, query: str, lingua: str = "it", solo_strumenti: bool = True, sessione: Any = None) -> list[bis.RisultatoRicerca]:
        self.search_calls.append((query, lingua))
        if query not in self.answers:
            pytest.fail(f"cerca called for {query!r}, which this test never offered")
        answer = self.answers[query]
        if isinstance(answer, BaseException):
            raise answer
        return copy.deepcopy(answer)

    def new_session(self, *args: Any, **kwargs: Any) -> FakeSession:
        session = FakeSession()
        self.sessions.append(session)
        return session

    @property
    def isins_called(self) -> list[str]:
        return [call[0] for call in self.calls]


def _every_session_closed_once(library: FakeLibrary) -> None:
    """Every library session the plugin opened is closed exactly once."""
    closes = [session.closes for session in library.sessions]
    assert closes == [1] * len(closes), f"each session closed exactly once: closes per session {closes}"


@pytest.fixture
def bi(monkeypatch: pytest.MonkeyPatch) -> Iterator[ModuleType]:
    """The plugin module, with the library replaced by stubs that fail the test (no network ever)."""
    module = importlib.import_module(PLUGIN_MODULE)
    monkeypatch.setattr(module, "ottieni_scheda", lambda *a, **k: pytest.fail(f"unpatched ottieni_scheda{a}"), raising=True)
    monkeypatch.setattr(module, "cerca", lambda *a, **k: pytest.fail(f"unpatched cerca{a}"), raising=True)
    monkeypatch.setattr(module, "Sessione", FakeSession, raising=True)
    yield module


@pytest.fixture
def library(bi: ModuleType, monkeypatch: pytest.MonkeyPatch) -> FakeLibrary:
    fake = FakeLibrary()
    monkeypatch.setattr(bi, "ottieni_scheda", fake.ottieni_scheda, raising=True)
    monkeypatch.setattr(bi, "cerca", fake.cerca, raising=True)
    monkeypatch.setattr(bi, "Sessione", fake.new_session, raising=True)
    return fake


@pytest.fixture
def plugin(bi: ModuleType, library: FakeLibrary):
    return bi.BorsaItalianaEnricher()


def _isin(isin: str, **params: Any) -> EnricherBinding:
    return EnricherBinding("ISIN", isin, params=params)


def _read_one(plugin, binding: EnricherBinding) -> EnricherReadItem:
    items = list(plugin.read([binding]))
    assert len(items) == 1 and items[0].index == 0, f"one item for one binding: {items}"
    return items[0]


def _by_index(items: list[EnricherReadItem], count: int) -> dict[int, EnricherReadItem]:
    indices = [item.index for item in items]
    assert sorted(indices) == list(range(count)), f"exactly one item per binding: {indices}"
    return {item.index: item for item in items}


def _stored(values: Any) -> dict[str, Any]:
    """Every yielded voice in its stored form: a value the catalogue refuses fails the test here."""
    return {key: normalize_value(key, value) for key, value in dict(values).items()}


def _give_recording(library: FakeLibrary, name: str, language: str = "en") -> str:
    sheet = _sheet(name, language)
    return library.give(sheet.isin, sheet, language)


def _read_recording(plugin, library: FakeLibrary, name: str, language: str = "en") -> EnricherReadItem:
    isin = _give_recording(library, name, language)
    params = {} if language == "en" else {"language": language}
    return _read_one(plugin, _isin(isin, **params))


def _synthetic(library: FakeLibrary, isin: str, base: str = "btp_valore", language: str = "en", **overrides: Any) -> EnricherBinding:
    """The recorded sheet ``base`` in ``language`` with ``overrides``, offered under ``isin``."""
    sheet = dataclasses.replace(_sheet(base, language), isin=isin, **overrides)
    library.give(isin, sheet, language)
    return _isin(isin, **({} if language == "en" else {"language": language}))


def _read_synthetic(plugin, library: FakeLibrary, isin: str, base: str = "btp_valore", language: str = "en", **overrides: Any) -> dict[str, Any]:
    item = _read_one(plugin, _synthetic(library, isin, base, language, **overrides))
    assert item.status == EnricherReadStatus.OK, f"a synthetic sheet is found: {item}"
    return _stored(item.values)


def _log_lines_naming(events: list[dict[str, Any]], text: str) -> list[dict[str, Any]]:
    return [event for event in events if text in repr(event)]


def _payout(name: str, language: str) -> dict[str, str]:
    text = (_sheet(name, language).descrizione_payout or "").strip()
    return {"payout_description": text} if text else {}


def _page(isin: str, language: str = "en", mic: str | None = None, platform: str | None = None) -> str:
    url = f"https://www.borsaitaliana.it/borsa/search/scheda.html?code={isin}&lang={language}"
    return url + (f"&mic={mic}" if mic else "") + (f"&platform={platform}" if platform else "")


def _param(plugin, key: str) -> dict[str, Any]:
    params = {param["key"]: param for param in plugin.params_schema}
    assert key in params, f"a binding param {key!r}: {sorted(params)}"
    return params[key]


# =============================================================================
# 0. The recordings themselves (green before C2: they check the fixtures, not the plugin)
# =============================================================================


@pytest.mark.parametrize("name", [*BONDS, "enel", "asml", "apple", "swda", "etf_bond"])
def test_recordings_rebuild_as_the_library_types(name):
    """Every recorded sheet has exactly the installed library's fields, and rebuilds with Decimal and date values."""
    recording = _recording(name)
    assert set(recording) == {"source", "asset", "version", "recorded_at", "calls"}, f"English envelope keys: {sorted(recording)}"
    for call in recording["calls"]:
        language = call.removeprefix("scheda_")
        if recording["calls"][call]["response"] is None:
            assert isinstance(_recorded_error(name, language), bis.StrumentoNonTrovato)
            continue
        sheet = _sheet(name, language)
        assert isinstance(sheet.prezzo, Decimal)
        if sheet.tipo == "obbligazione":
            assert isinstance(sheet.scadenza, date) and isinstance(sheet.rendimento_lordo, Decimal) and isinstance(sheet.data_prezzo_riferimento, date)


def test_expected_tables_are_stored_forms():
    """A guard on this file's own tables: each is a fixed point of the catalogue (``normalize_value``)."""
    tables = [*EXPECTED_BONDS_EN.values(), EXPECTED_BOND_CORP_IT, *EXPECTED_OTHERS.values()]
    for table in tables:
        assert _stored(table) == table


# =============================================================================
# 1. Declarations
# =============================================================================


def test_declarations(bi):
    cls = bi.BorsaItalianaEnricher
    assert cls.code == CODE
    assert cls.name == "Borsa Italiana"
    assert cls.terms is EnricherTerms.PRICE_SOURCE
    assert cls.accepted_identifier_types == ("ISIN",)
    assert not getattr(cls, "test_only", False), "a real enricher, served outside test mode"
    assert cls().supports_search is True


def test_coverage_and_voices(bi):
    cls = bi.BorsaItalianaEnricher
    assert set(cls.default_priority) == set(AssetType), "a degree for every AssetType"
    for asset_type in AssetType:
        expected = COVERED.get(asset_type)
        assert cls.default_priority[asset_type] == expected, f"{asset_type.value}: degree {cls.default_priority[asset_type]!r}, expected {expected!r}"
    assert cls.default_priority[AssetType.CRYPTO] is None, "CRYPTO stays uncovered (the recognize API test without codes relies on it)"
    assert set(cls.voices) == set(COVERED), f"voices for BOND and STOCK only: {sorted(t.value for t in cls.voices)}"
    assert "inception_date" not in cls.voices[AssetType.BOND], "correction C2-fix-1: the first day of trading is no launch date"
    assert cls.voices[AssetType.BOND] == BOND_VOICES, f"bond voices: {sorted(cls.voices[AssetType.BOND] ^ BOND_VOICES)}"
    assert cls.voices[AssetType.STOCK] == STOCK_VOICES
    assert BOND_VOICES <= set(CATALOGUE) and len(BOND_VOICES) == 20, "barrier: 20 catalogue voices"
    assert "description" not in cls.voices[AssetType.BOND], "no description in this lot"


def test_registered_and_served_in_production(bi, monkeypatch):
    monkeypatch.setenv(TEST_MODE_VARIABLE, "1")
    assert is_test_mode() is True, "barrier: test mode on"
    assert EnricherRegistry.get_plugin(CODE) is bi.BorsaItalianaEnricher
    failures = [failure for failure in EnricherRegistry.get_discovery_errors() if CODE in repr(failure)]
    assert failures == [], f"borsa_italiana failed to load: {failures}"
    with monkeypatch.context() as patch:
        patch.setenv(TEST_MODE_VARIABLE, "0")
        assert is_test_mode() is False, "barrier: production"
        assert CODE in EnricherRegistry.list_plugin_codes(), "not test-only: listed on a production instance"
        assert EnricherRegistry.get_plugin(CODE) is bi.BorsaItalianaEnricher


def test_binding_params_mic_and_platform(plugin):
    """The same keys as the price plugin's binding (``codice_fondo`` aside: funds are not in this lot); only keys,
    types and defaults are pinned, the texts are the i18n fragment's. (``language`` and the whole key set: section
    «Language».)"""
    for key in ("mic", "platform"):
        param = _param(plugin, key)
        assert param["type"] == "string", f"{key}: {param}"
        assert not param.get("required", False), f"{key} is optional: {param}"
        assert param.get("default") in (None, ""), f"{key} has no default: {param}"
        assert str(param.get("x-i18n-key", "")).startswith(I18N_PREFIX), f"{key}: an x-i18n-key under {I18N_PREFIX}*: {param}"


def test_test_cases_for_the_external_suite(plugin):
    cases = plugin.test_cases
    assert cases, "test_cases for the external suite"
    types = set()
    for case in cases:
        assert case["binding"]["identifier_type"] == "ISIN", case
        asset_type = AssetType(case["asset_type"])
        assert plugin.voices.get(asset_type), f"a case of a type with declared voices: {case}"
        types.add(asset_type)
    assert AssetType.BOND in types, f"at least one bond: {cases}"


def _plugin_imports() -> list[str]:
    tree = ast.parse(Path(importlib.util.find_spec(PLUGIN_MODULE).origin).read_text(encoding="utf-8"))
    imported = [node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
    return imported + [alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names]


def test_no_import_from_the_price_plugin(bi):
    """The two plugins of Borsa Italiana share nothing (plan §C, rule 1): no import from ``asset_source_providers``."""
    imported = _plugin_imports()
    assert not [name for name in imported if "asset_source_providers" in name], f"imports from the price plugin: {imported}"


def test_the_annual_coupon_comes_from_financial_math(bi):
    """One home for financial math: the plugin takes the annual coupon from ``financial_math``, no local copy."""
    imported = _plugin_imports()
    assert any(name.startswith("backend.app.services.financial_math") for name in imported), f"no import from financial_math: {imported}"


@pytest.mark.parametrize(
    ("params", "url"),
    [
        ({}, _page("IT0005565400")),
        ({"mic": "MOTX"}, _page("IT0005565400", mic="MOTX")),
        ({"mic": "ETLX", "platform": "TLX"}, _page("IT0005565400", mic="ETLX", platform="TLX")),
        ({"platform": "TLX"}, _page("IT0005565400", platform="TLX")),
    ],
    ids=["bare", "mic", "mic-platform", "platform"],
)
def test_page_url(plugin, params, url):
    assert plugin.page_url(_isin("IT0005565400", **params)) == url


# =============================================================================
# 2. Mapping: the recorded bonds
# =============================================================================


@pytest.mark.parametrize("name", BONDS)
def test_bond_recording_stored_forms(plugin, library, name):
    item = _read_recording(plugin, library, name)

    assert item.status == EnricherReadStatus.OK, f"{name}: {item}"
    assert item.source_date is None, "no date for the whole sheet"
    assert all(value is not None for value in item.values.values()), f"a voice the page does not give is absent, never None: {item.values}"
    assert set(item.values) <= BOND_VOICES, f"only the declared bond voices: {sorted(set(item.values) - BOND_VOICES)}"
    expected = {**EXPECTED_BONDS_EN[name], **_payout(name, "en")}
    stored = _stored(item.values)
    assert stored == expected, f"{name}: stored forms differ\n got      {stored}\n expected {expected}"
    isin = _sheet(name).isin
    assert library.calls == [(isin, None, "en", None)], f"one sheet call, English by default, no mic or platform: {library.calls}"


@pytest.mark.parametrize("name", BONDS)
def test_bond_recording_dates_the_as_of_voices(plugin, library, name):
    """Yields, duration and accrued interest are «as of» the reference price date; nothing else is dated."""
    item = _read_recording(plugin, library, name)
    assert item.status == EnricherReadStatus.OK, item
    assert _sheet(name).data_prezzo_riferimento == REFERENCE_DATE, "barrier: the recording's reference price date"
    assert dict(item.source_dates) == dict.fromkeys(AS_OF_VOICES, REFERENCE_DATE), f"{name}: {dict(item.source_dates)}"
    assert AS_OF_VOICES <= set(item.values)


@pytest.mark.parametrize("name", ["btp_ord", "btp_2072"])
@pytest.mark.parametrize("language", LANGUAGES)
def test_missing_annual_coupon_is_period_times_coupons_per_year(plugin, library, name, language):
    """The ordinary BTPs give only the period coupon: 3.00 → 6 %, 1.075 → 2.15 %, semiannual."""
    sheet = _sheet(name, language)
    assert sheet.cedola_annua is None and sheet.cedola_periodale is not None, "barrier: only the period coupon is given"
    stored = _stored(_read_recording(plugin, library, name, language).values)
    assert stored["coupon_rate"] == EXPECTED_BONDS_EN[name]["coupon_rate"]
    assert stored["coupon_period_rate"] == EXPECTED_BONDS_EN[name]["coupon_period_rate"]


@pytest.mark.parametrize("name", ["btp_valore", "btp_italia", "austria_2117"])
@pytest.mark.parametrize("language", LANGUAGES)
def test_given_annual_coupon_agrees_with_period_times_coupons(plugin, library, name, language):
    """Where the page gives both, the period coupon times the coupons per year is the annual coupon: on the sheet
    itself, through ``annual_coupon_rate``, and on the stored voices."""
    from backend.app.services.financial_math.interest import COUPONS_PER_YEAR, annual_coupon_rate  # noqa: PLC0415 — red on its own until C2

    sheet = _sheet(name, language)
    assert sheet.cedola_annua is not None and sheet.cedola_periodale is not None, "barrier: both coupons given"
    stored = _stored(_read_recording(plugin, library, name, language).values)
    frequency = stored["coupon_frequency"]
    assert annual_coupon_rate(sheet.cedola_periodale, frequency) == sheet.cedola_annua
    assert Decimal(stored["coupon_period_rate"]) * COUPONS_PER_YEAR[frequency] == Decimal(stored["coupon_rate"])


# =============================================================================
# 2. Mapping: the recorded stocks and an ETF
# =============================================================================


@pytest.mark.parametrize("name", sorted(EXPECTED_OTHERS))
def test_stock_and_other_recording_stored_forms(plugin, library, name):
    item = _read_recording(plugin, library, name)
    assert item.status == EnricherReadStatus.OK, f"{name}: found: {item}"
    assert set(item.values) <= STOCK_VOICES, f"a stock gives sector and legal form only: {sorted(item.values)}"
    assert _stored(item.values) == EXPECTED_OTHERS[name]
    assert item.source_date is None and dict(item.source_dates) == {}, "nothing dated"


def test_a_sheet_of_another_type_is_found_with_no_values(plugin, library):
    item = _read_one(plugin, _synthetic(library, "IT00TESTOT001", base="enel", tipo="altro", settore="Utilities"))
    assert item.status == EnricherReadStatus.OK
    assert dict(item.values) == {} and dict(item.source_dates) == {}


def test_a_stock_takes_no_bond_field(plugin, library):
    """A share sheet carrying bond fields (synthetic) still gives sector and legal form only."""
    stored = _read_synthetic(plugin, library, "IT00TESTST001", base="enel", scadenza=date(2030, 1, 1), rendimento_lordo=Decimal("3.1"), emittente="Enel S.p.A.")
    assert stored == EXPECTED_OTHERS["enel"]


@pytest.mark.parametrize("name", ["Space Mining", "Servizi pubblici"], ids=["english", "italian"])
def test_a_share_sector_the_helper_does_not_know_is_absent_and_logged_once(plugin, library, name):
    """Correction C2b-2. A sector name the generic helper (``utils/asset/sector.py``) does not know leaves ``sector``
    out, with one log line naming it: stored, it would be «Other» at 100 %, which says nothing. The legal form stays."""
    assert not validate_sector(name), f"barrier: the helper does not know {name!r}"
    assert normalize_value("sector", {name: "1"}) == {"Other": "1.0000"}, "barrier: the catalogue would store «Other» at 100 %"
    binding = _synthetic(library, "IT00TESTSS001", base="enel", settore=name)
    with capture_logs() as events:
        item = _read_one(plugin, binding)
    assert item.status == EnricherReadStatus.OK, item
    assert "sector" not in item.values, f"an unknown sector is left out: {item.values}"
    assert _stored(item.values) == {"legal_form": "share"}
    assert len(_log_lines_naming(events, name)) == 1, f"one log line names the sector: {events}"


@pytest.mark.parametrize(("name", "stored"), [("Utilities", "Utilities"), ("Technology", "Technology"), ("Healthcare", "Health Care")])
def test_a_share_sector_the_helper_knows_goes_on_as_it_is(plugin, library, name, stored):
    """The helper is asked first: a name it knows (an alias included) is passed on as it is, the catalogue normalises it;
    no log line."""
    assert validate_sector(name), f"barrier: the helper knows {name!r}"
    binding = _synthetic(library, "IT00TESTSS002", base="enel", settore=name)
    with capture_logs() as events:
        item = _read_one(plugin, binding)
    assert set(item.values["sector"]) == {name}, f"passed on as it is: {item.values}"
    assert _stored(item.values) == {"sector": {stored: "1.0000"}, "legal_form": "share"}
    assert _log_lines_naming(events, name) == [], f"a known sector is not logged: {events}"


# =============================================================================
# 2. Mapping: synthetic bond sheets
# =============================================================================


@pytest.mark.parametrize(
    ("language", "text", "code"),
    [
        ("en", "Monthly", "monthly"),
        ("en", "Quarterly", "quarterly"),
        ("en", "Semiannually", "semiannual"),
        ("en", "Annually", "annual"),
        ("en", "12 Months", "annual"),  # recorded: EuroTLX
        ("en", "6 Months", "semiannual"),  # no recording
        ("en", "3 Months", "quarterly"),  # no recording
        ("en", "1 Month", "monthly"),  # no recording
        ("it", "Mensile", "monthly"),
        ("it", "Trimestrale", "quarterly"),
        ("it", "Semestrale", "semiannual"),
        ("it", "Annuale", "annual"),
    ],
)
def test_coupon_frequency_texts(plugin, library, language, text, code):
    stored = _read_synthetic(plugin, library, "IT00TESTFQ001", language=language, frequenza_cedola=text)
    assert stored.get("coupon_frequency") == code


def test_unknown_coupon_frequency_is_absent_and_logged_once(plugin, library):
    binding = _synthetic(library, "IT00TESTFQ002", frequenza_cedola="Biennial")
    with capture_logs() as events:
        item = _read_one(plugin, binding)
    assert item.status == EnricherReadStatus.OK
    assert "coupon_frequency" not in item.values
    assert len(_log_lines_naming(events, "Biennial")) == 1, f"one log line names the text: {events}"
    assert _stored(item.values)["coupon_rate"] == "0.045", "the given annual coupon is still read"


@pytest.mark.parametrize(
    ("language", "text", "code"),
    [
        ("en", "Structured Interest Rate", "structured"),
        ("it", "Stuctured Interest Rate", "structured"),  # the Italian page's own misspelling, recorded
        ("en", "Inflation Linked", "inflation_linked"),
        ("it", "Titoli Indicizzati All'inflazione", "inflation_linked"),
        ("en", "Plain Vanilla", None),
        ("it", "Plain Vanilla", None),
        ("en", None, None),
    ],
)
def test_coupon_type_texts(plugin, library, language, text, code):
    stored = _read_synthetic(plugin, library, "IT00TESTCT001", language=language, struttura_bond=text)
    assert stored.get("coupon_type") == code


def test_plain_vanilla_is_silent_an_unknown_structure_is_logged(plugin, library):
    """«Plain Vanilla» says no special structure — not fixed, not floating: absent, with no log line. An unknown text, read
    in the same call, is absent with exactly one."""
    plain = _synthetic(library, "IT00TESTCT002", struttura_bond="Plain Vanilla")
    unknown = _synthetic(library, "IT00TESTCT003", struttura_bond="Lab Exotic Structure")
    with capture_logs() as events:
        items = _by_index(list(plugin.read([plain, unknown])), 2)
    assert all(item.status == EnricherReadStatus.OK and "coupon_type" not in item.values for item in items.values()), items
    assert len(_log_lines_naming(events, "Lab Exotic Structure")) == 1, f"one log line names the unknown structure: {events}"
    assert _log_lines_naming(events, "Plain Vanilla") == [], f"Plain Vanilla is not logged: {events}"


@pytest.mark.parametrize(("text", "code"), [("ACT/ACT (ICMA)", "act_act_icma"), ("ACT/ACT (PERIODIC BASIS)", "act_act_icma"), (None, None)])
def test_day_count_texts(plugin, library, text, code):
    stored = _read_synthetic(plugin, library, "IT00TESTDC001", convenzione_giorni=text)
    assert stored.get("day_count") == code


def test_unknown_day_count_is_absent_and_logged_once(plugin, library):
    binding = _synthetic(library, "IT00TESTDC002", convenzione_giorni="ACT/360")
    with capture_logs() as events:
        item = _read_one(plugin, binding)
    assert item.status == EnricherReadStatus.OK and "day_count" not in item.values
    assert len(_log_lines_naming(events, "ACT/360")) == 1, f"one log line names the text: {events}"


@pytest.mark.parametrize(
    ("language", "text", "issuer_type", "sector"),
    [
        ("en", "Italian Government Bonds", "sovereign", GOVERNMENT),
        ("it", "Titoli di stato italiani", "sovereign", GOVERNMENT),
        ("en", "Foreign Public Debt", "sovereign", GOVERNMENT),
        ("it", "Titoli di stato esteri", "sovereign", GOVERNMENT),
        ("it", "Obbligazioni Finanziarie", "corporate", CORPORATE),
        # no recording: the wordings the price plugin's sector table knows (``_TIPOLOGIA_TO_SECTOR``)
        ("en", "Corporate Bonds", "corporate", CORPORATE),
        ("en", "Supranational Bonds", "supranational", None),
        ("it", "Obbligazioni Sovranazionali", "supranational", None),
        # unknown or absent: neither voice
        ("en", "Lab Category", None, None),
        ("en", None, None, None),
    ],
)
def test_issuer_type_and_sector(plugin, library, language, text, issuer_type, sector):
    stored = _read_synthetic(plugin, library, "IT00TESTIT001", language=language, tipologia=text)
    assert stored.get("issuer_type") == issuer_type
    assert stored.get("sector") == sector


@pytest.mark.parametrize(
    ("issuer", "country"),
    [("REPUBLIC OF ITALY", "ITA"), ("REPUBLIC OF AUSTRIA", "AUT"), ("KINGDOM OF ATLANTIS", None)],
)
def test_sovereign_issuer_country_and_geography(plugin, library, issuer, country):
    """A sovereign issuer through the plugin's own table: its country, and a geography of that one country; an issuer
    the table does not know gives neither (no guessing), the rest of the sheet unchanged."""
    stored = _read_synthetic(plugin, library, "IT00TESTIC001", emittente=issuer)
    assert stored["issuer_type"] == "sovereign" and stored["sector"] == GOVERNMENT, "barrier: a sovereign sheet"
    assert stored["issuer_name"] == issuer
    assert stored.get("issuer_country") == country
    assert stored.get("geography") == ({country: "1.0000"} if country else None)


def test_percent_fields_are_fractions_and_may_be_negative(plugin, library):
    stored = _read_synthetic(plugin, library, "IT00TESTPC001", rendimento_lordo=Decimal("-0.25"), rendimento_netto=Decimal("-0.3"), cedola_annua=Decimal("0"), cedola_periodale=Decimal("0"))
    assert (stored["yield_gross"], stored["yield_net"]) == ("-0.0025", "-0.003")
    assert (stored["coupon_rate"], stored["coupon_period_rate"]) == ("0", "0")


def test_duration_and_accrued_interest_are_not_percents(plugin, library):
    stored = _read_synthetic(plugin, library, "IT00TESTDU001", duration_modificata=Decimal("12.5"), rateo_lordo=Decimal("1.25"))
    assert (stored["modified_duration"], stored["accrued_interest"]) == ("12.5", "1.25")


def test_outstanding_amount_in_the_sheet_currency(plugin, library):
    stored = _read_synthetic(plugin, library, "XS00TESTOA001", outstanding=Decimal("500000000"), valuta="USD")
    assert stored["outstanding_amount"] == {"amount": "500000000", "currency": "USD"}


# Correction C2-fix-2: the outstanding amount is in the denomination currency (``valuta_denominazione``) when the page
# gives it, else in the trading currency (``valuta``). Assumed: «denomination only» covers both absent forms of
# ``valuta``, the empty text (the library types it ``str``) and None.


@pytest.mark.parametrize("trading", ["", None], ids=["empty-valuta", "none-valuta"])
def test_outstanding_amount_in_the_denomination_currency_alone(plugin, library, trading):
    binding = _synthetic(library, "XS00TESTOA002", outstanding=Decimal("500000000"), valuta=trading, valuta_denominazione="GBP")
    with capture_logs() as events:
        item = _read_one(plugin, binding)
    assert item.status == EnricherReadStatus.OK, f"a sheet with no trading currency is still read: {item}"
    stored = _stored(item.values)
    assert stored.get("outstanding_amount") == {"amount": "500000000", "currency": "GBP"}, f"the denomination currency when the trading one is absent: {stored.get('outstanding_amount')!r}"
    assert _log_lines_naming(events, "GBP") == [], f"nothing to log: {events}"


def test_outstanding_amount_both_currencies_equal(plugin, library):
    """Green today, a guard: both given and equal, the amount in that currency, no log line."""
    binding = _synthetic(library, "XS00TESTOA003", outstanding=Decimal("500000000"), valuta="GBP", valuta_denominazione="GBP")
    with capture_logs() as events:
        item = _read_one(plugin, binding)
    assert item.status == EnricherReadStatus.OK, item
    assert _stored(item.values).get("outstanding_amount") == {"amount": "500000000", "currency": "GBP"}
    assert _log_lines_naming(events, "GBP") == [], f"nothing to log: {events}"


def test_outstanding_amount_currencies_differ_is_absent_and_logged_once(plugin, library):
    """Both given and different: which one the amount is in is unknown, so no outstanding amount, with exactly one log
    line naming both currencies; the rest of the sheet is still read."""
    binding = _synthetic(library, "XS00TESTOA004", outstanding=Decimal("500000000"), valuta="CHF", valuta_denominazione="GBP")
    with capture_logs() as events:
        item = _read_one(plugin, binding)
    assert item.status == EnricherReadStatus.OK, item
    assert "outstanding_amount" not in item.values, f"no outstanding amount when the currencies differ: {item.values.get('outstanding_amount')!r}"
    naming_either = [event for event in events if "CHF" in repr(event) or "GBP" in repr(event)]
    assert len(naming_either) == 1, f"exactly one log line about the currencies: {events}"
    assert "CHF" in repr(naming_either[0]) and "GBP" in repr(naming_either[0]), f"the line names both currencies: {naming_either[0]}"
    assert _stored(item.values)["maturity_date"] == "2028-10-10", "the other voices stay"


@pytest.mark.parametrize(("trading", "denomination"), [("CHF", "GBP"), (None, "GBP"), ("CHF", None)], ids=["differ", "denomination-only", "valuta-only"])
def test_no_outstanding_amount_is_absent_and_silent(plugin, library, trading, denomination):
    """Green today, a guard: without an amount there is no voice and nothing to log, also when the currencies differ
    (an implementation that compares the currencies before looking at the amount would log here)."""
    binding = _synthetic(library, "XS00TESTOA005", outstanding=None, valuta=trading, valuta_denominazione=denomination)
    with capture_logs() as events:
        item = _read_one(plugin, binding)
    assert item.status == EnricherReadStatus.OK, item
    assert "outstanding_amount" not in item.values
    assert [event for event in events if "CHF" in repr(event) or "GBP" in repr(event)] == [], f"nothing to log: {events}"


# Correction C2-fix-1: a bond writes no ``inception_date``.


@pytest.mark.parametrize("name", BONDS)
@pytest.mark.parametrize("language", LANGUAGES)
def test_no_bond_recording_writes_an_inception_date(plugin, library, name, language):
    item = _read_recording(plugin, library, name, language)
    assert item.status == EnricherReadStatus.OK, item
    assert "inception_date" not in item.values, f"{name} {language}: the first day of trading is not a launch date: {item.values.get('inception_date')!r}"


@pytest.mark.parametrize("base", ["btp_ord", "bond_corp"])
def test_a_first_day_of_trading_writes_no_inception_date(plugin, library, base):
    """Synthetic: whatever ``data_primo_giorno`` says (``bond_corp`` has none recorded), no ``inception_date``."""
    stored = _read_synthetic(plugin, library, "IT00TESTIN001", base=base, data_primo_giorno=date(2008, 11, 3))
    assert "inception_date" not in stored, f"{base}: {stored.get('inception_date')!r}"


def test_the_given_annual_coupon_wins(plugin, library):
    """An annual coupon on the page is taken as it is, even when the period coupon says otherwise."""
    stored = _read_synthetic(plugin, library, "IT00TESTCR001", cedola_annua=Decimal("5.00"), cedola_periodale=Decimal("1.00"), frequenza_cedola="Quarterly")
    assert (stored["coupon_rate"], stored["coupon_period_rate"]) == ("0.05", "0.01")


@pytest.mark.parametrize("frequency", [None, "Biennial"], ids=["no-frequency", "unknown-frequency"])
def test_no_annual_coupon_without_a_known_frequency(plugin, library, frequency):
    """No annual coupon on the page and no frequency to multiply by: no coupon rate, the period coupon still given."""
    stored = _read_synthetic(plugin, library, "IT00TESTCR002", cedola_annua=None, cedola_periodale=Decimal("1.5"), frequenza_cedola=frequency)
    assert "coupon_rate" not in stored
    assert stored["coupon_period_rate"] == "0.015"


def test_monthly_period_coupon_gives_the_annual_rate(plugin, library):
    stored = _read_synthetic(plugin, library, "IT00TESTCR003", cedola_annua=None, cedola_periodale=Decimal("0.5"), frequenza_cedola="Monthly")
    assert (stored["coupon_rate"], stored["coupon_frequency"]) == ("0.06", "monthly")


def test_no_reference_date_dates_nothing(plugin, library):
    """Without a reference price date, no voice is dated and ``reference_price_date`` is absent; the values stay."""
    item = _read_one(plugin, _synthetic(library, "IT00TESTRD001", data_prezzo_riferimento=None))
    assert item.status == EnricherReadStatus.OK
    assert dict(item.source_dates) == {} and item.source_date is None
    stored = _stored(item.values)
    expected = {key: value for key, value in EXPECTED_BONDS_EN["btp_valore"].items() if key != "reference_price_date"}
    assert stored == {**expected, **_payout("btp_valore", "en")}


def test_only_the_as_of_voices_given_are_dated(plugin, library):
    item = _read_one(plugin, _synthetic(library, "IT00TESTRD002", rendimento_lordo=None, rateo_lordo=None))
    assert item.status == EnricherReadStatus.OK
    assert dict(item.source_dates) == {"yield_net": REFERENCE_DATE, "modified_duration": REFERENCE_DATE}
    assert "yield_gross" not in item.values and "accrued_interest" not in item.values


def test_the_page_description_is_never_read(plugin, library):
    """The sheet's ``descrizione`` is the page's advertising line: changing it changes nothing."""
    first = _synthetic(library, "IT00TESTDS001", descrizione="Real time quotes")
    second = _synthetic(library, "IT00TESTDS002", descrizione="Something else entirely")
    items = _by_index(list(plugin.read([first, second])), 2)
    assert _stored(items[0].values) == _stored(items[1].values)
    assert "description" not in items[0].values


# =============================================================================
# 3. Language (the binding's «language» param; kept together: it may become an instance setting)
# =============================================================================


def test_language_param(plugin):
    """``language`` is a binding param beside ``mic`` and ``platform``, the price plugin's keys (``codice_fondo`` aside:
    funds are not in this lot). The other language cases of this file go through ``_read_recording`` and
    ``_synthetic``, which put ``language`` in the binding's params: the one place to change if it becomes a setting."""
    assert {param["key"] for param in plugin.params_schema} == {"language", "mic", "platform"}
    param = _param(plugin, "language")
    assert param["type"] == "select"
    assert set(param["options"]) == {"en", "it"}
    assert param.get("default") == "en"
    assert not param.get("required", False)
    assert str(param.get("x-i18n-key", "")).startswith(I18N_PREFIX), f"language: an x-i18n-key under {I18N_PREFIX}*: {param}"


def test_the_binding_language_is_the_page_asked(plugin, library):
    isin = _give_recording(library, "btp_valore", "it")
    item = _read_one(plugin, _isin(isin, language="it"))
    assert item.status == EnricherReadStatus.OK
    assert library.calls == [(isin, None, "it", None)]
    assert _stored(item.values)["payout_description"] == _payout("btp_valore", "it")["payout_description"], "the Italian text"


def test_page_url_in_the_binding_language(plugin):
    assert plugin.page_url(_isin("IT0005565400", language="it", mic="MOTX")) == _page("IT0005565400", "it", mic="MOTX")


def test_recognize_asks_the_binding_language(plugin, library):
    isin = _give_recording(library, "btp_ord", "it")
    assert plugin.recognize(_isin(isin, language="it")).found is True
    assert library.calls == [(isin, None, "it", None)]


@pytest.mark.parametrize("name", MOT_BONDS)
def test_language_invariance_of_the_mot_bonds(plugin, library, name):
    """English and Italian pages: the same stored values for every voice but the payout text."""
    english = _read_recording(plugin, library, name, "en")
    italian = _read_recording(plugin, library, name, "it")
    assert english.status == italian.status == EnricherReadStatus.OK
    texts = {"payout_description"}
    english_stored = {key: value for key, value in _stored(english.values).items() if key not in texts}
    italian_stored = {key: value for key, value in _stored(italian.values).items() if key not in texts}
    assert english_stored == italian_stored, f"{name}: EN and IT differ: {sorted(set(english_stored.items()) ^ set(italian_stored.items()), key=str)}"
    assert english_stored == {key: value for key, value in EXPECTED_BONDS_EN[name].items() if key not in texts}
    assert dict(english.source_dates) == dict(italian.source_dates)
    assert set(_payout(name, "en")) == set(_payout(name, "it")), "barrier: both pages give a payout text, or neither"
    assert _stored(italian.values).get("payout_description") == _payout(name, "it").get("payout_description")


@pytest.mark.parametrize(("language", "expected"), [("en", EXPECTED_BONDS_EN["bond_corp"]), ("it", EXPECTED_BOND_CORP_IT)])
def test_eurotlx_pages_as_they_are(plugin, library, language, expected):
    """EuroTLX breaks the invariance: the English page has «12 Months» and no tipologia, the Italian one the reverse."""
    item = _read_recording(plugin, library, "bond_corp", language)
    assert item.status == EnricherReadStatus.OK
    assert _stored(item.values) == expected
    assert dict(item.source_dates) == dict.fromkeys(AS_OF_VOICES, REFERENCE_DATE)


# =============================================================================
# 4. Not found
# =============================================================================


def test_recorded_unresolved_sheet_is_not_found(plugin, library):
    """The recorded ``StrumentoNonRisolto`` of an ETF the universal page did not resolve."""
    error = _recorded_error("etf_bond")
    isin = "IE00B3F81409"
    assert isin in str(error), "barrier: the recorded error names the ISIN"
    library.give(isin, error)
    assert _read_one(plugin, _isin(isin)).status == EnricherReadStatus.NOT_FOUND
    assert plugin.recognize(_isin(isin)).found is False


@pytest.mark.parametrize("error_class", [bis.StrumentoNonTrovato, bis.StrumentoNonRisolto])
def test_not_found_errors(plugin, library, error_class):
    isin = library.give("IT00TESTNF001", error_class("not found"))
    item = _read_one(plugin, _isin(isin))
    assert item.status == EnricherReadStatus.NOT_FOUND and item.error_code is None, item
    assert plugin.recognize(_isin(isin)).found is False


# =============================================================================
# 5. recognize
# =============================================================================


def test_recognize_found(plugin, library):
    sheet = _sheet("btp_valore")
    library.give(sheet.isin, sheet)
    assert plugin.recognize(_isin(sheet.isin)) == EnricherRecognition(found=True, name=sheet.nome, page_url=sheet.url_pagina, identifiers={})
    assert library.calls == [(sheet.isin, None, "en", None)]


def test_recognize_passes_mic_and_platform(plugin, library):
    sheet = _sheet("bond_corp")
    library.give(sheet.isin, sheet)
    assert plugin.recognize(_isin(sheet.isin, mic="ETLX", platform="TLX")).found is True
    assert library.calls == [(sheet.isin, "ETLX", "en", "TLX")]


def test_recognize_without_a_page_url_uses_the_plugins(plugin, library):
    binding = _synthetic(library, "IT00TESTRC001", url_pagina=None)
    recognition = plugin.recognize(binding)
    assert recognition.found is True and recognition.page_url == plugin.page_url(binding) == _page("IT00TESTRC001")


@pytest.mark.parametrize("binding", [EnricherBinding("TICKER", "ENEL"), EnricherBinding("LEI", "815600C1E8D1A8C6E417")])
def test_recognize_non_isin_without_a_call(plugin, library, binding):
    assert plugin.recognize(binding).found is False
    assert library.calls == []


def test_recognize_rate_limited_raises(plugin, library):
    """The library's refusal (a 403 from the firewall, no «429» in its text) must reach the core as a refusal."""
    assert rate_limited_from_exception(bis.RateLimitRaggiunto(WAF_MESSAGE), CODE) is None, "barrier: the core cannot read the bare library error"
    isin = library.give("IT00TESTRL001", bis.RateLimitRaggiunto(WAF_MESSAGE))
    with pytest.raises(Exception) as raised:
        plugin.recognize(_isin(isin))
    assert rate_limited_from_exception(raised.value, CODE) is not None, f"the core must read it as a refusal: {raised.value!r}"


@pytest.mark.parametrize("error", [bis.ErroreConnessione("timeout"), ValueError("unexpected page layout")])
def test_recognize_other_errors_raise(plugin, library, error):
    isin = library.give("IT00TESTRE001", error)
    with pytest.raises(Exception) as raised:
        plugin.recognize(_isin(isin))
    assert rate_limited_from_exception(raised.value, CODE) is None, f"not a refusal: {raised.value!r}"


# =============================================================================
# 6. read
# =============================================================================


def test_read_mixed_list(plugin, library):
    valore = _give_recording(library, "btp_valore")
    enel = _give_recording(library, "enel")
    unresolved = library.give("IE00B3F81409", _recorded_error("etf_bond"))
    bindings = [_isin(valore), EnricherBinding("TICKER", "ENEL"), _isin(unresolved), _isin(enel)]

    items = _by_index(list(plugin.read(bindings)), len(bindings))

    assert [items[i].status for i in range(4)] == [EnricherReadStatus.OK, EnricherReadStatus.NOT_FOUND, EnricherReadStatus.NOT_FOUND, EnricherReadStatus.OK]
    assert _stored(items[3].values) == EXPECTED_OTHERS["enel"]
    assert library.isins_called == [valore, unresolved, enel], "no call for the ticker"


def test_read_passes_each_bindings_params(plugin, library):
    corp = _give_recording(library, "bond_corp")
    ord_ = _give_recording(library, "btp_ord")
    items = _by_index(list(plugin.read([_isin(corp, mic="ETLX", platform="TLX"), _isin(ord_, mic="MOTX")])), 2)
    assert all(item.status == EnricherReadStatus.OK for item in items.values())
    assert library.calls == [(corp, "ETLX", "en", "TLX"), (ord_, "MOTX", "en", None)]


@pytest.mark.parametrize("error", [bis.ErroreConnessione("timeout"), bis.DatiNonDisponibili("no data"), ValueError("unexpected page layout")])
def test_read_library_error_is_an_error_item_and_the_next_is_read(plugin, library, error):
    failing = library.give("IT00TESTER001", error)
    valore = _give_recording(library, "btp_valore")

    items = _by_index(list(plugin.read([_isin(failing), _isin(valore)])), 2)

    assert items[0].status == EnricherReadStatus.ERROR and items[0].error_code == SOURCE_ERROR, items[0]
    assert items[1].status == EnricherReadStatus.OK
    assert library.isins_called == [failing, valore]


def test_read_rate_limited_defers_every_remaining_binding(plugin, library):
    ord_ = _give_recording(library, "btp_ord")
    refused = library.give("IT00TESTRL002", bis.RateLimitRaggiunto(WAF_MESSAGE))
    # never offered: a call for either fails the test
    bindings = [_isin(ord_), _isin(refused), _isin("IT00TESTRL003"), _isin("IT00TESTRL004")]

    items = _by_index(list(plugin.read(bindings)), len(bindings))

    assert items[0].status == EnricherReadStatus.OK
    for index in (1, 2, 3):
        assert items[index].status == EnricherReadStatus.ERROR and items[index].error_code == RATE_LIMITED, f"binding {index}: {items[index]}"
    assert library.isins_called == [ord_, refused], "no call after the refusal"


def test_one_session_per_read(plugin, library):
    """One library ``Sessione`` per ``read``, handed to every call of it; the next ``read`` opens its own."""
    names = ("btp_valore", "btp_ord", "enel")
    bindings = [_isin(_give_recording(library, name)) for name in names]

    first = _by_index(list(plugin.read(bindings)), 3)
    assert all(item.status == EnricherReadStatus.OK for item in first.values())
    assert len(library.sessions) == 1, f"one session for the read: {library.sessions}"
    assert library.call_sessions == [library.sessions[0]] * 3, "every call of the read gets that session"

    second = _by_index(list(plugin.read(bindings[:1])), 1)
    assert second[0].status == EnricherReadStatus.OK
    assert len(library.sessions) == 2 and library.call_sessions[-1] is library.sessions[1], "the next read opens its own"


def test_the_read_session_is_closed_after_a_normal_read(plugin, library):
    """Correction C2b-1: the session of a ``read`` is closed exactly once, after its last call."""
    bindings = [_isin(_give_recording(library, name)) for name in ("btp_valore", "enel")]
    items = _by_index(list(plugin.read(bindings)), 2)
    assert all(item.status == EnricherReadStatus.OK for item in items.values())
    assert len(library.sessions) == 1, "barrier: one session for the read"
    _every_session_closed_once(library)


@pytest.mark.parametrize(
    "error",
    [bis.ErroreConnessione("timeout"), ValueError("unexpected page layout"), bis.RateLimitRaggiunto(WAF_MESSAGE)],
    ids=["connection", "other", "rate-limited"],
)
def test_the_read_session_is_closed_when_a_binding_fails(plugin, library, error):
    """A failing binding, a refusal included: the read goes on to the end, and its session is still closed once."""
    failing = library.give("IT00TESTSC001", error)
    valore = _give_recording(library, "btp_valore")
    bindings = [_isin(failing), _isin(valore)]
    if isinstance(error, bis.RateLimitRaggiunto):
        bindings = [_isin(valore), _isin(failing), _isin("IT00TESTSC002")]  # never offered: deferred without a call
    items = _by_index(list(plugin.read(bindings)), len(bindings))
    assert any(item.status == EnricherReadStatus.ERROR for item in items.values()), f"barrier: a binding failed: {items}"
    assert len(library.sessions) == 1, "barrier: one session for the read"
    _every_session_closed_once(library)


def test_the_read_session_is_closed_when_the_consumer_stops_early(plugin, library):
    """The consumer takes the first item and closes the generator: the session is closed once, no further call."""
    bindings = [_isin(_give_recording(library, name)) for name in ("btp_valore", "btp_ord", "enel")]
    reading = plugin.read(bindings)
    first = next(reading)
    assert first.status == EnricherReadStatus.OK, first
    reading.close()
    assert len(library.sessions) == 1, "barrier: one session for the read"
    _every_session_closed_once(library)
    assert len(library.calls) == 1, f"no call after the consumer stopped: {library.calls}"


# =============================================================================
# 7. search
# =============================================================================


def _hit(isin: str, mic: str, nome: str, tipo: str, mercato: str) -> bis.RisultatoRicerca:
    return bis.RisultatoRicerca(isin=isin, mic=mic, nome=nome, tipo=tipo, mercato=mercato)


SEARCH_HITS = [
    (_hit("IT0005565400", "MOTX", "Btp Valore Sc Oct28 Eur", "Obbligazione", "MOT"), AssetType.BOND),
    (_hit("IT0003128367", "MTAA", "Enel", "Azione", "Euronext Milan"), AssetType.STOCK),
    (_hit("IE00B4L5Y983", "ETFP", "Ishares Core Msci World Ucits Etf Acc", "ETF", "ETFplus"), None),
    (_hit("IE00B4ND3602", "ETFP", "Ishares Physical Gold Etc", "ETC/ETN", "ETFplus"), None),
]


def test_search(plugin, library):
    library.answers["lab query"] = [hit for hit, _ in SEARCH_HITS]

    results = plugin.search("lab query")

    assert library.search_calls == [("lab query", "it")], f"cerca(query, lingua='it'): {library.search_calls}"
    assert library.calls == [], "search reads the site's search, never a sheet"
    assert all(isinstance(result, EnricherSearchResult) for result in results)
    expected = []
    for hit, asset_type in SEARCH_HITS:
        binding = EnricherBinding("ISIN", hit.isin, params={"mic": hit.mic})
        expected.append(EnricherSearchResult(name=hit.nome, binding=binding, asset_type=asset_type, page_url=plugin.page_url(binding)))
    assert results == expected, f"one result per hit, in order:\n got      {results}\n expected {expected}"


def test_search_with_no_hit(plugin, library):
    library.answers["zz-nothing-zz"] = []
    assert plugin.search("zz-nothing-zz") == []


def test_the_search_session_is_closed(plugin, library):
    """Correction C2b-1: ``search`` opens one session and closes it exactly once."""
    library.answers["lab query"] = [hit for hit, _ in SEARCH_HITS]
    assert len(plugin.search("lab query")) == len(SEARCH_HITS)
    assert len(library.sessions) == 1, f"one session for the search: {library.sessions}"
    _every_session_closed_once(library)


@pytest.mark.parametrize("error", [bis.RicercaNonDisponibile("search blocked"), bis.ErroreConnessione("timeout")], ids=["unavailable", "connection"])
def test_the_search_session_is_closed_when_cerca_raises(plugin, library, error):
    """``cerca`` fails: whatever ``search`` then does with the error, its session is closed exactly once."""
    library.answers["lab failing query"] = error
    with contextlib.suppress(Exception):
        plugin.search("lab failing query")
    assert library.search_calls == [("lab failing query", "it")], "barrier: cerca was called"
    assert len(library.sessions) == 1, f"one session for the search: {library.sessions}"
    _every_session_closed_once(library)
