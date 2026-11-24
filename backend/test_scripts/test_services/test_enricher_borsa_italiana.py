"""
The Borsa Italiana enricher (plan 68, lot C2): ``enricher_providers/borsa_italiana/plugin.py``, class
``BorsaItalianaEnricher``. Bonds first, the sector of a stock, and two voices of a mutual fund (lot C2b, section 8).

What it promises, pinned here with no network:

1. **Declarations**: ``code`` ``borsa_italiana``, ``name`` ``Borsa Italiana``, ``terms`` ``PRICE_SOURCE``, identifier
   types ``ISIN`` and ``BI_FUND_CODE`` (the site's internal fund code, C2b), not test-only. ``BOND`` and ``FUND`` at
   degree 10, ``STOCK`` at degree 20 (Yahoo, a later lot, leads stocks), every other type ``None`` (``CRYPTO`` among
   them: the recognize API test without ``codes`` relies on it). Twenty-one bond voices (``description`` among them
   since C2d), never ``inception_date`` (correction C2-fix-1); ``sector`` and ``legal_form`` for a stock, plus
   ``description``, ``issuer_country``, ``website``, ``revenue`` and ``net_income`` when the library has
   ``ottieni_profilo_societa`` (lot BI-PROF: declared at import, from the plugin's own ``try``/``except ImportError``;
   seven stock voices with it, written out as a literal); ``fund_currency`` and ``inception_date`` for a fund. Binding params ``language`` (select ``en``/``it``, default
   ``en``, not required), ``mic``, ``platform`` and ``codice_fondo`` (strings, not required), each with an
   ``x-i18n-key`` under ``enrichers.borsa_italiana.`` (the texts are the implementer's: only keys and defaults are
   pinned). ``test_cases`` for the external suite. No import from the price plugin of the same name
   (``asset_source_providers/``).

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
     A ``description`` composed from stable facts only (C2d, plan I19), in the binding's language: kind (from the
     issuer type), issuer (for a state the country's name from pycountry, EN or IT; else the page's issuer as written),
     coupon type (structured or inflation-linked only), frequency, then «; » and the maturity, month in words from a
     fixed table, day without a leading zero (Italian: «il 1º», «l'8», «l'11», else «il D»; English: the plain day);
     never a price, a yield, the annual coupon or the first day of trading. Composed only when at least one fact beyond
     the kind is known (issuer, frequency, coupon type or maturity): otherwise no ``description`` at all, never «Bond.»
     or «Obbligazione.» (a source with nothing to say must not replace the ``legacy`` text).
     The expected sentences are written out (``DESCRIPTIONS``), never built with pycountry or a month table here.
     Never ``inception_date`` (correction C2-fix-1): the page's ``data_primo_giorno`` is a venue's first day of
     trading, not a launch date (BTP 6 % 2031 shows 2008-11-03 on an ISIN of the late-90s series). The outstanding
     amount is in ``valuta_denominazione`` when the page gives it, else in ``valuta`` (correction C2-fix-2); both given
     and different: no outstanding amount, one log line naming both currencies. No bond recording gives
     ``valuta_denominazione`` (only the ETF ``swda`` does), so their stored forms are unchanged by it;
   - a stock (``tipo == "azione"``), from its sheet: ``sector`` (one sector at 100 %) when the sheet gives one the
     generic helper (``utils/asset/sector.py``) knows, passed on as it is; a name it does not know leaves ``sector`` out
     with one log line, never «Other» at 100 % (correction C2b-2); ``legal_form`` ``share``, nothing else from the
     sheet. From the company profile page (lot BI-PROF, section 9), when the plugin's module-level
     ``ottieni_profilo_societa`` is not None: ``description`` ← ``descrizione`` (in the binding's language, as written)
     and ``issuer_country`` ← the ISO alpha-3 of ``indirizzo.paese`` (generic helper ``normalize_country_to_iso3``; a
     name it does not know leaves the voice out with one log line) and ``website`` ← ``contatti.sito_web``, those
     three dated by ``ultimo_aggiornamento``; ``revenue`` and ``net_income`` from the «main data» table, dated by the
     end of their fiscal year (section 9). The
     per-share pins of this section offer no profile: the plugin asks it, the fake library answers the library's «not
     found», so they test the sheet's voices alone;
   - any other ``tipo`` (an ETF): found, OK, no values;
   - **per-voice dates**: yields, modified duration and accrued interest are «as of» the reference price date, given in
     ``source_dates`` for those of the four the item gives; nothing else is dated, the item's ``source_date`` stays None;
   - **language**: the binding's ``language`` is the page asked (``lingua``). For each MOT bond the English and the
     Italian page give the same stored values but for ``payout_description`` and ``description``, texts in the page's
     language. The EuroTLX
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
   generator early (correction C2b-1). A share whose sheet is read makes one more call, ``ottieni_profilo_societa(isin,
   mic, lingua, sessione=<the read's session>)``, paced as any other, only when ``keys`` is None or asks one of
   the profile's five voices; ``mic`` is the binding's (upper case), else the one in the sheet's
   ``url_pagina`` (``…/<ISIN>-<MIC>.html``), else None. Bonds, funds, ETFs and other sheets never make it. On that call
   ``StrumentoNonTrovato`` / ``StrumentoNonRisolto`` → the sheet's voices, OK; ``RateLimitRaggiunto`` → that item
   ``ERROR`` ``RATE_LIMITED`` and every binding after it the same, without a call; any other error → the sheet's
   voices, OK, one log line (section 9).

5. **search**: ``cerca(query, lingua="it", sessione=…)``, the session closed exactly once, also when ``cerca``
   raises (correction C2b-1; recognize's session is the library's own, unpinned); one result per hit, bound by ISIN with the hit's ``mic``,
   ``BOND`` for a bond, ``STOCK`` for a share, ``None`` otherwise, with the plugin's page of that binding.

6. **page_url**: ``https://www.borsaitaliana.it/borsa/search/scheda.html?code=<ISIN>&lang=<language>``, then
   ``&mic=…`` and ``&platform=…`` when the binding has them (the price plugin's form). A fund binding (C2b):
   ``https://www.borsaitaliana.it/borsa/fondi/dettaglio/<code>.html?lang=<language>``, the price plugin's rule.

8. **Funds** (lot C2b). The site's search does not find a mutual fund by its ISIN (the recording's ``cerca_isin`` answers
   ``[]``): a fund is reached by the internal code the price assignment keeps in ``provider_params.codice_fondo``
   (``1FADB716664`` for Anima Dinamix). A ``BI_FUND_CODE`` binding, and an ``ISIN`` binding whose params carry a
   non-empty ``codice_fondo``, read ``ottieni_dati_fondo(code, sessione=…)``, never ``ottieni_scheda``; any other ISIN
   binding stays on the sheet. Voices: ``fund_currency`` ← ``valuta``; ``inception_date`` ← ``caratteristiche["Data di
   partenza"]`` (dd/mm/yy or dd/mm/yyyy; two-digit years pivot on today's year), absent when missing or unparsable.
   Never ``ter`` («Gestione» is the management fee), ``fund_size`` (no unit), ``fund_provider`` (not guessed),
   ``description``, nor a risk grade or category (no catalogue voice). ``recognize``: the fund's name, its page, and
   ``{"ISIN": …}`` when the page gives one (a strong identifier for the cascade, plan B4). ``StrumentoNonTrovato`` and
   ``DatiNonDisponibili`` of a fund → not found; ``RateLimitRaggiunto`` → a refusal, as on the sheet path; the
   session rules of the read are the sheet's. The recording ``mutual_fund.json`` rebuilds the library's ``DatiFondo``.

9. **Company profile of a share** (lot BI-PROF). The recording ``enel_profile.json`` (the library's own test pages for
   Enel, ``profilo_en`` / ``profilo_it``) rebuilds a ``ProfiloSocieta``: the library's own class when the installed
   library has it, else a stand-in with the same field names (pinned equal to the library's when both exist). Enel:
   the description of each page as written, ``issuer_country`` ``ITA`` («Italy» on both pages) and ``website``
   ``https://www.enel.com/investors/overview``, dated 2026-10-23; ``revenue`` 78 057 000 000 EUR and ``net_income``
   5 617 000 000 EUR («78057» and «5617» in «EUR - millions» / «EUR - milioni»), dated 2025-12-31 (the fiscal year
   end of 2025). Website: kept when it starts with ``http(s)://``, «https://» put before a bare domain (``www.x.com``,
   ``x.com/path``), anything else (``mailto:``, an e-mail address, ``ftp://``, a word) absent with one warning; blank or
   no contacts, absent and silent. Figures: the rows «Net sales»/«Fatturato» and «Net income»/«Utile netto» (any case;
   never «Net income (Group share)»/«Utile netto: quota del gruppo»), the most recent year with a number (an empty cell
   falls back to the year before, each figure on its own), scaled by that year's «Currency & Unit» / «Valuta e unità di
   misura» (units/unità ×1, thousands/migliaia ×1 000, millions/milioni ×10⁶, billions/miliardi ×10⁹; the currency the
   part before « - »), dated by that year's «Fiscal year end» / «Chiusura esercizio fiscale». An unknown unit: both
   figures absent, one warning; no unit or no fiscal year end for that year: that figure absent, silent (never an older
   year's date). The synthetic tables are built with the library's ``DatoSocietario``. The tests drive the plugin's module-level ``ottieni_profilo_societa``, so they run with either library;
   the declaration is pinned by executing the plugin's source again, with and without the library's function, under
   another module name and with the registration neutralised (the registered module is never reloaded).

No network, by construction: the plugin module is imported in a fixture, which replaces ``ottieni_scheda``, ``cerca``,
``Sessione`` and ``ottieni_profilo_societa`` (BI-PROF, ``raising=False``) on it (``raising=True``: the names must be imported at module level into the plugin) with fakes. The fake
library answers only the ``(isin, lingua)`` pairs a test offered and fails the test (``pytest.fail``, a
``BaseException`` no plugin ``except Exception`` swallows) for any other call; the fake session fails on any request.
``ottieni_dati_fondo`` is replaced the same way but with ``raising=False`` (red before C2b: the plugin does not import
it yet, and ``raising=True`` would fail every test of this file at its fixture);
``test_the_fund_reader_is_imported_at_module_level`` pins the module-level import instead, and the library's own
``ottieni_dati_fondo`` is replaced by a failing stub for every test, so a plugin reaching it another way still makes no
request. The one exception to «anything not offered fails the test»: a company profile the test did not offer answers
the library's ``StrumentoNonTrovato`` (the old pins on shares keep their meaning, the sheet's voices alone), so every
«never asks the profile» claim is pinned on the profile's own call log (``profile_calls``), kept apart from the sheet's;
the library's own ``ottieni_profilo_societa``, when it has one, fails the test. Assumed: the plugin keeps no sheet,
fund or profile cache of its own (the read cache is the core's), so the call logs are exact.

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
import threading
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
    EnricherRateLimited,
    EnricherReadItem,
    EnricherReadStatus,
    EnricherRecognition,
    EnricherSearchResult,
    EnricherTerms,
)
from backend.app.services.enrichers.registry import EnricherRegistry
from backend.app.services.plugin_settings.call_limits import CALL_LIMIT_KEYS
from backend.app.utils.asset.geo import normalize_country_to_iso3
from backend.app.utils.asset.sector import validate_sector
from backend.app.utils.runtime.pacing import Pacer

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
        "description",
    }
)
STOCK_VOICES = frozenset({"sector", "legal_form"})
#: BI-PROF: the voices of the company profile page dated by its last update.
PAGE_VOICES = frozenset({"description", "issuer_country", "website"})
#: BI-PROF: the two figures of a fiscal year, dated by its end.
FISCAL_VOICES = frozenset({"revenue", "net_income"})
#: BI-PROF: the voices of the company profile page, a stock's only when the library reads that page.
PROFILE_VOICES = PAGE_VOICES | FISCAL_VOICES
#: BI-PROF: read once at collection, before any fixture patches the library: the installed library has the reader.
LIBRARY_HAS_PROFILE = hasattr(bis, "ottieni_profilo_societa")
#: C2b: exactly the two fund voices the fund page gives with a unit and a meaning.
FUND_VOICES = frozenset({"fund_currency", "inception_date", "management_fee"})
COVERED = {AssetType.BOND: 10, AssetType.STOCK: 20, AssetType.FUND: 10}
#: C2b: the identifier type of the site's internal fund code, and the recorded fund (Anima Dinamix).
FUND_CODE_TYPE = "BI_FUND_CODE"
FUND_CODE = "1FADB716664"
FUND_ISIN = "IT0005487001"
FUND_RECORDING = "mutual_fund"
#: The recorded fund in stored form: «EUR», «14/03/22».
EXPECTED_FUND = {"fund_currency": "EUR", "inception_date": "2022-03-14", "management_fee": "0.004"}
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

#: C2d: the composed description of every recorded bond, per page language (the consultant's four sentences, the
#: others derived by the same rule from the recordings). Literal: never rebuilt with pycountry or a month table.
DESCRIPTIONS: dict[tuple[str, str], str] = {
    ("btp_valore", "en"): "Government bond, issuer Italy, structured interest rate, paying quarterly; matures on 10 October 2028.",
    ("btp_valore", "it"): "Titolo di Stato, emittente Italia, a tasso strutturato, con cedola trimestrale; scade il 10 ottobre 2028.",
    ("btp_ord", "en"): "Government bond, issuer Italy, paying semiannually; matures on 1 May 2031.",
    # day 1 in Italian: «1º» (U+00BA, the masculine ordinal indicator)
    ("btp_ord", "it"): "Titolo di Stato, emittente Italia, con cedola semestrale; scade il 1\u00ba maggio 2031.",
    ("btp_italia", "en"): "Government bond, issuer Italy, inflation-linked, paying semiannually; matures on 4 June 2032.",
    ("btp_italia", "it"): "Titolo di Stato, emittente Italia, indicizzato all'inflazione, con cedola semestrale; scade il 4 giugno 2032.",
    ("btp_2072", "en"): "Government bond, issuer Italy, paying semiannually; matures on 1 March 2072.",
    ("btp_2072", "it"): "Titolo di Stato, emittente Italia, con cedola semestrale; scade il 1\u00ba marzo 2072.",
    ("austria_2117", "en"): "Government bond, issuer Austria, paying annually; matures on 20 September 2117.",
    ("austria_2117", "it"): "Titolo di Stato, emittente Austria, con cedola annuale; scade il 20 settembre 2117.",
    # EuroTLX: the English page has no tipologia (kind «Bond») but «12 Months»; the Italian one the reverse
    ("bond_corp", "en"): "Bond, issuer Anima Holding S.P.A., paying annually; matures on 22 April 2028.",
    ("bond_corp", "it"): "Obbligazione societaria, emittente Anima Holding S.P.A.; scade il 22 aprile 2028.",
}

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
        description=DESCRIPTIONS[("btp_valore", "en")],
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
        description=DESCRIPTIONS[("btp_ord", "en")],
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
        description=DESCRIPTIONS[("btp_italia", "en")],
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
        description=DESCRIPTIONS[("btp_2072", "en")],
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
        "description": DESCRIPTIONS[("austria_2117", "en")],
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
        "description": DESCRIPTIONS[("bond_corp", "en")],
    },
}

#: EuroTLX, Italian page: no coupon frequency at all; «Obbligazioni Finanziarie» → a corporate issuer.
EXPECTED_BOND_CORP_IT = {
    **{key: value for key, value in EXPECTED_BONDS_EN["bond_corp"].items() if key != "coupon_frequency"},
    "issuer_type": "corporate",
    "sector": CORPORATE,
    "description": DESCRIPTIONS[("bond_corp", "it")],
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
_FUND_FIELDS = tuple(field.name for field in dataclasses.fields(bis.DatiFondo))
_FUND_HINTS = typing.get_type_hints(bis.DatiFondo)


def _recording(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


def _call(name: str, language: str) -> dict[str, Any]:
    return _recording(name)["calls"][f"scheda_{language}"]


def _typed(field: str, value: Any, hints: dict[str, Any] = _HINTS) -> Any:
    """A recorded JSON value as the library's field type (of ``SchedaStrumento`` by default, or of the class whose
    ``hints`` are given): text → ``Decimal`` or ``date``, never a plain string."""
    if value is None:
        return None
    hint = hints[field]
    if typing.get_origin(hint) is dict:
        assert isinstance(value, dict) and all(isinstance(k, str) and isinstance(v, str) for k, v in value.items()), f"{field}: a dict of texts, got {value!r}"
        return dict(value)
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


def _fund(name: str = FUND_RECORDING) -> bis.DatiFondo:
    """The recorded ``DatiFondo`` of ``name`` (``ottieni_dati_fondo``), with the library's real types."""
    response = _recording(name)["calls"]["ottieni_dati_fondo"]["response"]
    assert response is not None, f"barrier: {name} recorded a fund page"
    assert set(response) == set(_FUND_FIELDS), f"{name}: the recording does not match the installed library: {sorted(set(response) ^ set(_FUND_FIELDS))}"
    return bis.DatiFondo(**{field: _typed(field, response[field], _FUND_HINTS) for field in _FUND_FIELDS})


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
        self.funds: dict[str, Any] = {}
        self.fund_calls: list[str] = []
        self.fund_call_sessions: list[Any] = []
        self.profiles: dict[tuple[str, str], Any] = {}
        self.profile_calls: list[tuple[str, str | None, str]] = []
        self.profile_call_sessions: list[Any] = []

    def give(self, isin: str, answer: Any, language: str = "en") -> str:
        self.sheets[(isin, language)] = answer
        return isin

    def give_fund(self, code: str, answer: Any) -> str:
        """C2b: offer a fund page (a ``DatiFondo``, or an exception to raise) under its internal code."""
        self.funds[code] = answer
        return code

    def ottieni_dati_fondo(self, codice: str, sessione: Any = None) -> bis.DatiFondo:
        self.fund_calls.append(codice)
        self.fund_call_sessions.append(sessione)
        if isinstance(sessione, FakeSession) and sessione.closes:
            pytest.fail(f"ottieni_dati_fondo called for {codice!r} on a session already closed")
        if codice not in self.funds:
            pytest.fail(f"ottieni_dati_fondo called for {codice!r}, which this test never offered (a call the contract forbids, or a fetch from borsaitaliana.it)")
        answer = self.funds[codice]
        if isinstance(answer, BaseException):
            raise answer
        return copy.deepcopy(answer)

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

    def give_profile(self, isin: str, answer: Any, language: str = "en") -> str:
        """BI-PROF: offer a company profile (a ``ProfiloSocieta``, or an exception to raise) for ``(isin, lingua)``."""
        self.profiles[(isin, language)] = answer
        return isin

    def ottieni_profilo_societa(self, isin: str, mic: str | None = None, lingua: str = "en", sessione: Any = None) -> Any:
        """BI-PROF: a profile not offered is the library's «not found» (no page for it), never a request."""
        self.profile_calls.append((isin, mic, lingua))
        self.profile_call_sessions.append(sessione)
        if isinstance(sessione, FakeSession) and sessione.closes:
            pytest.fail(f"ottieni_profilo_societa called for {isin!r} on a session already closed")
        answer = self.profiles.get((isin, lingua), bis.StrumentoNonTrovato(f"no profile offered for {isin} {lingua}"))
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

    # C2b: raising=False, the plugin does not import it before C2b (test_the_fund_reader_is_imported_at_module_level
    # pins the import); the library's own entry points fail too, whichever way the plugin reaches them
    def unpatched_fund(*a: Any, **k: Any) -> Any:
        pytest.fail(f"unpatched ottieni_dati_fondo{a}")

    monkeypatch.setattr(module, "ottieni_dati_fondo", unpatched_fund, raising=False)
    monkeypatch.setattr(bis, "ottieni_dati_fondo", unpatched_fund, raising=True)
    monkeypatch.setattr(bis.fondi, "ottieni_dati_fondo", unpatched_fund, raising=True)

    # BI-PROF: raising=False, a plugin older than the lot has no such name; the library's own reader fails too, only
    # where the installed library has it (adding it to an older library would make LIBRARY_HAS_PROFILE lie)
    def unpatched_profile(*a: Any, **k: Any) -> Any:
        pytest.fail(f"unpatched ottieni_profilo_societa{a}")

    monkeypatch.setattr(module, "ottieni_profilo_societa", unpatched_profile, raising=False)
    if LIBRARY_HAS_PROFILE:
        monkeypatch.setattr(bis, "ottieni_profilo_societa", unpatched_profile, raising=True)
        monkeypatch.setattr(bis.scheda, "ottieni_profilo_societa", unpatched_profile, raising=True)
    yield module


@pytest.fixture
def library(bi: ModuleType, monkeypatch: pytest.MonkeyPatch) -> FakeLibrary:
    fake = FakeLibrary()
    monkeypatch.setattr(bi, "ottieni_scheda", fake.ottieni_scheda, raising=True)
    monkeypatch.setattr(bi, "cerca", fake.cerca, raising=True)
    monkeypatch.setattr(bi, "Sessione", fake.new_session, raising=True)
    monkeypatch.setattr(bi, "ottieni_dati_fondo", fake.ottieni_dati_fondo, raising=False)
    monkeypatch.setattr(bi, "ottieni_profilo_societa", fake.ottieni_profilo_societa, raising=False)
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


def _description(item: EnricherReadItem) -> str:
    """The item's composed description (C2d) in stored form; fails with «no description» when it is absent."""
    assert item.status == EnricherReadStatus.OK, f"barrier: the sheet is read: {item}"
    assert "description" in item.values, f"C2d: a bond gets a composed description; voices given: {sorted(item.values)}"
    return normalize_value("description", item.values["description"])


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
    for key, sentence in DESCRIPTIONS.items():
        assert normalize_value("description", sentence) == sentence, f"{key}: a stored text"
    assert set(DESCRIPTIONS) == {(name, language) for name in BONDS for language in LANGUAGES}, "a sentence per bond page"


# =============================================================================
# 1. Declarations
# =============================================================================


def test_declarations(bi):
    cls = bi.BorsaItalianaEnricher
    assert cls.code == CODE
    assert cls.name == "Borsa Italiana"
    assert cls.terms is EnricherTerms.PRICE_SOURCE
    assert cls.accepted_identifier_types == ("ISIN", FUND_CODE_TYPE), "C2b: the ISIN, and the site's internal fund code"
    assert not getattr(cls, "test_only", False), "a real enricher, served outside test mode"
    own = tuple(field.key for field in cls.settings_fields if field.key not in CALL_LIMIT_KEYS)
    assert own == (), "no settings of its own"
    assert tuple(field.key for field in cls.settings_fields if field.key in CALL_LIMIT_KEYS) == CALL_LIMIT_KEYS, "it calls a source: the core gives it the five call limits (76 U4)"
    assert cls().supports_search is True


def test_coverage_and_voices(bi):
    cls = bi.BorsaItalianaEnricher
    assert set(cls.default_priority) == set(AssetType), "a degree for every AssetType"
    for asset_type in AssetType:
        expected = COVERED.get(asset_type)
        assert cls.default_priority[asset_type] == expected, f"{asset_type.value}: degree {cls.default_priority[asset_type]!r}, expected {expected!r}"
    assert cls.default_priority[AssetType.CRYPTO] is None, "CRYPTO stays uncovered (the recognize API test without codes relies on it)"
    assert set(cls.voices) == set(COVERED), f"voices for BOND, STOCK and FUND only: {sorted(t.value for t in cls.voices)}"
    assert "inception_date" not in cls.voices[AssetType.BOND], "correction C2-fix-1: the first day of trading is no launch date"
    assert cls.voices[AssetType.BOND] == BOND_VOICES, f"bond voices: {sorted(cls.voices[AssetType.BOND] ^ BOND_VOICES)}"
    stock = STOCK_VOICES | (PROFILE_VOICES if LIBRARY_HAS_PROFILE else frozenset())
    assert cls.voices[AssetType.STOCK] == stock, f"BI-PROF: the profile's voices only with a library that reads it (has it: {LIBRARY_HAS_PROFILE}): {sorted(cls.voices[AssetType.STOCK])}"
    assert BOND_VOICES <= set(CATALOGUE) and len(BOND_VOICES) == 21, "barrier: 21 catalogue voices"
    assert "description" in cls.voices[AssetType.BOND], "C2d: the composed description is a bond voice"
    assert ("description" in cls.voices[AssetType.STOCK]) is LIBRARY_HAS_PROFILE, "C2d: no composed description for a share; BI-PROF: the profile page's, with a library that reads it"
    if LIBRARY_HAS_PROFILE:
        assert cls.voices[AssetType.STOCK] == {"sector", "legal_form", "description", "issuer_country", "website", "revenue", "net_income"}, "BI-PROF: seven stock voices, written out"
    assert set(cls.voices[AssetType.STOCK]) <= set(CATALOGUE), "barrier: catalogue voices"
    assert cls.voices[AssetType.FUND] == FUND_VOICES, f"C2b, C2e: the fund currency, the inception date and the management fee: {sorted(cls.voices[AssetType.FUND])}"
    assert FUND_VOICES <= set(CATALOGUE), "barrier: catalogue voices"


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
    """The same keys as the price plugin's binding (``codice_fondo`` since C2b); only keys, types and defaults are
    pinned, the texts are the i18n fragment's. (``language`` and the whole key set: section «Language».)"""
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
        assert case["binding"]["identifier_type"] in ("ISIN", FUND_CODE_TYPE), case
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
    """The sheet's voices alone: no profile page is offered (section 9 for the profile's)."""
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
        # no recording: wordings the site uses for other bond lists (the price plugin's old sector table, gone in plan 68 D6)
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
    """The sheet's ``descrizione`` is the page's advertising line: changing it changes nothing, and the composed
    description (C2d) never carries it."""
    first = _synthetic(library, "IT00TESTDS001", descrizione="Real time quotes")
    second = _synthetic(library, "IT00TESTDS002", descrizione="Something else entirely")
    items = _by_index(list(plugin.read([first, second])), 2)
    assert _description(items[0]) == DESCRIPTIONS[("btp_valore", "en")], "barrier: the composed sentence is there"
    assert _stored(items[0].values) == _stored(items[1].values)
    assert "Real time quotes" not in _description(items[0]) and "Something else" not in _description(items[1])


# =============================================================================
# 2. Mapping: the composed description (C2d, plan I19)
# =============================================================================
#
# A bond page has no prose about the instrument (its ``descrizione`` is an advertisement), so the plugin composes one
# sentence from stable facts only, in the binding's language: kind, issuer, coupon type (structured or inflation-linked
# only), frequency — joined by «, » — then «; » and the maturity, ending with «.». Never a price, a yield, the annual
# coupon or the first day of trading. Every expected sentence below is a literal.
#
# The Italian day (consultant's answer): day 1 is «1º» (U+00BA), days 8 and 11 elide the article («l'8», «l'11», ASCII
# apostrophe as in «all'inflazione»), every other day is «il D»; English is the plain day. Only the kind known (no
# issuer, frequency, coupon type or maturity): no description at all.
#
# Synthetic sheets use a maturity of 5 June 2030 (a single-digit day, no leading zero) unless the case is the maturity.

SYNTHETIC_MATURITY = date(2030, 6, 5)
MATURES = {"en": "; matures on 5 June 2030.", "it": "; scade il 5 giugno 2030."}


def _synthetic_description(plugin, library: FakeLibrary, isin: str, base: str = "btp_ord", language: str = "en", **overrides: Any) -> str:
    overrides.setdefault("scadenza", SYNTHETIC_MATURITY)
    return _description(_read_one(plugin, _synthetic(library, isin, base, language, **overrides)))


@pytest.mark.parametrize("language", LANGUAGES)
@pytest.mark.parametrize("name", BONDS)
def test_description_of_each_bond_recording(plugin, library, name, language):
    """The exact sentence of every recorded bond page, in that page's language."""
    item = _read_recording(plugin, library, name, language)
    assert _description(item) == DESCRIPTIONS[(name, language)]


@pytest.mark.parametrize("language", LANGUAGES)
@pytest.mark.parametrize("name", BONDS)
def test_description_is_a_catalogue_text(plugin, library, name, language):
    """The yielded value is a text the catalogue stores as it is (``normalize_value``: no stray space, not empty)."""
    item = _read_recording(plugin, library, name, language)
    assert "description" in item.values, f"C2d: a bond gets a composed description: {sorted(item.values)}"
    raw = item.values["description"]
    assert isinstance(raw, str), f"a text: {raw!r}"
    assert normalize_value("description", raw) == raw, f"a fixed point of the catalogue: {raw!r}"


@pytest.mark.parametrize("language", LANGUAGES)
@pytest.mark.parametrize("name", BONDS)
def test_description_never_carries_the_page_advert(plugin, library, name, language):
    """The page's ``descrizione`` (an advertisement) is never the description, nor any part of it."""
    advert = _sheet(name, language).descrizione
    assert advert, "barrier: the page has its advertising line"
    description = _description(_read_recording(plugin, library, name, language))
    assert description != advert.strip()
    assert advert.strip() not in description
    assert _sheet(name, language).isin not in description, f"no part of the advert (its ISIN in brackets): {description!r}"


def test_no_description_for_shares_and_other_sheets(plugin, library):
    """Only a bond gets a description composed from its sheet: not a share, not an ETF (read beside a bond, which does
    get one). No profile page is offered: a share's description from its profile page is section 9."""
    names = ("btp_valore", "enel", "asml", "apple", "swda")
    bindings = [_isin(_give_recording(library, name)) for name in names]
    items = _by_index(list(plugin.read(bindings)), len(names))
    assert _description(items[0]) == DESCRIPTIONS[("btp_valore", "en")], "barrier: the bond beside them has one"
    for index, name in enumerate(names[1:], start=1):
        assert items[index].status == EnricherReadStatus.OK, f"{name}: {items[index]}"
        assert "description" not in items[index].values, f"{name}: no description: {items[index].values.get('description')!r}"


def test_no_description_for_a_share_with_bond_fields(plugin, library):
    """A share sheet carrying bond fields (synthetic) still gets no description (read beside a bond, which does)."""
    bond = _isin(_give_recording(library, "btp_valore"))
    share = _synthetic(library, "IT00TESTDE001", base="enel", scadenza=date(2030, 1, 1), emittente="Enel S.p.A.", frequenza_cedola="Annually")
    items = _by_index(list(plugin.read([bond, share])), 2)
    assert _description(items[0]) == DESCRIPTIONS[("btp_valore", "en")], "barrier: the bond beside it has one"
    assert items[1].status == EnricherReadStatus.OK and "description" not in items[1].values, items[1]


@pytest.mark.parametrize(
    ("language", "expected"),
    [
        ("en", "Government bond, issuer Italy, structured interest rate, paying quarterly."),
        ("it", "Titolo di Stato, emittente Italia, a tasso strutturato, con cedola trimestrale."),
    ],
    ids=LANGUAGES,
)
def test_description_without_a_maturity(plugin, library, language, expected):
    """No maturity: no «; …» part, the sentence ends after the last of the first four parts."""
    item = _read_one(plugin, _synthetic(library, "IT00TESTDE002", "btp_valore", language, scadenza=None))
    assert "maturity_date" not in item.values, "barrier: no maturity"
    assert _description(item) == expected


@pytest.mark.parametrize(
    ("language", "issuer", "expected"),
    [
        ("en", None, "Government bond, structured interest rate, paying quarterly; matures on 10 October 2028."),
        ("it", None, "Titolo di Stato, a tasso strutturato, con cedola trimestrale; scade il 10 ottobre 2028."),
        ("en", "  ", "Government bond, structured interest rate, paying quarterly; matures on 10 October 2028."),
    ],
    ids=["en-none", "it-none", "en-blank"],
)
def test_description_without_an_issuer(plugin, library, language, issuer, expected):
    """No issuer: the issuer part is omitted, the kind still comes from the issuer type."""
    item = _read_one(plugin, _synthetic(library, "IT00TESTDE003", "btp_valore", language, emittente=issuer))
    assert "issuer_name" not in item.values and item.values.get("issuer_type") == "sovereign", "barrier: a sovereign sheet with no issuer"
    assert _description(item) == expected


@pytest.mark.parametrize(
    ("language", "tipologia", "kind"),
    [
        ("en", "Corporate Bonds", "Corporate bond, issuer Lab Issuer S.p.A."),
        ("it", "Obbligazioni Finanziarie", "Obbligazione societaria, emittente Lab Issuer S.p.A."),
        ("en", "Supranational Bonds", "Supranational bond, issuer Lab Issuer S.p.A."),
        ("it", "Obbligazioni Sovranazionali", "Obbligazione sovranazionale, emittente Lab Issuer S.p.A."),
        ("en", "Lab Category", "Bond, issuer Lab Issuer S.p.A."),
        ("en", None, "Bond, issuer Lab Issuer S.p.A."),
        ("it", None, "Obbligazione, emittente Lab Issuer S.p.A."),
    ],
)
def test_description_kind_from_the_issuer_type(plugin, library, language, tipologia, kind):
    """The kind from ``issuer_type`` (unknown or absent: plain «Bond»); a company issuer is written as the page has it."""
    frequency = {"en": ", paying semiannually", "it": ", con cedola semestrale"}[language]
    description = _synthetic_description(plugin, library, "IT00TESTDE004", language=language, tipologia=tipologia, emittente="Lab Issuer S.p.A.")
    assert description == f"{kind}{frequency}{MATURES[language]}"


@pytest.mark.parametrize(
    ("issuer", "english", "italian"),
    [
        ("REPUBLIC OF AUSTRIA", "Austria", "Austria"),
        ("FEDERAL REPUBLIC OF GERMANY", "Germany", "Germania"),
        ("KINGDOM OF THE NETHERLANDS", "Netherlands", "Paesi Bassi"),
        ("UNITED STATES OF AMERICA", "United States", "Stati Uniti"),
        ("UNITED KINGDOM", "United Kingdom", "Regno Unito"),
        # a state the plugin's table does not know: no country, the issuer as the page writes it
        ("REPUBLIC OF ATLANTIS", "REPUBLIC OF ATLANTIS", "REPUBLIC OF ATLANTIS"),
    ],
)
@pytest.mark.parametrize("language", LANGUAGES)
def test_description_state_issuer_is_the_country_name(plugin, library, issuer, english, italian, language):
    """A state issuer is named by its country, in the sentence's language (pycountry's offline names); a state the
    table does not know keeps the page's issuer."""
    tipologia = {"en": "Foreign Public Debt", "it": "Titoli di stato esteri"}[language]
    item = _read_one(plugin, _synthetic(library, "IT00TESTDE005", "btp_ord", language, tipologia=tipologia, emittente=issuer, scadenza=SYNTHETIC_MATURITY))
    assert item.values.get("issuer_type") == "sovereign", "barrier: a sovereign sheet"
    expected = {
        "en": f"Government bond, issuer {english}, paying semiannually{MATURES['en']}",
        "it": f"Titolo di Stato, emittente {italian}, con cedola semestrale{MATURES['it']}",
    }[language]
    assert _description(item) == expected


@pytest.mark.parametrize(
    ("language", "text", "part"),
    [
        ("en", "Structured Interest Rate", ", structured interest rate"),
        ("it", "Stuctured Interest Rate", ", a tasso strutturato"),
        ("en", "Inflation Linked", ", inflation-linked"),
        ("it", "Titoli Indicizzati All'inflazione", ", indicizzato all'inflazione"),
        ("en", "Plain Vanilla", ""),
        ("it", "Plain Vanilla", ""),
        ("en", "Lab Exotic Structure", ""),
        ("en", None, ""),
    ],
)
def test_description_coupon_type(plugin, library, language, text, part):
    """Only a structured or an inflation-linked coupon is said; anything else leaves the part out."""
    start = {"en": "Government bond, issuer Italy", "it": "Titolo di Stato, emittente Italia"}[language]
    frequency = {"en": ", paying semiannually", "it": ", con cedola semestrale"}[language]
    description = _synthetic_description(plugin, library, "IT00TESTDE006", language=language, struttura_bond=text)
    assert description == f"{start}{part}{frequency}{MATURES[language]}"


@pytest.mark.parametrize(
    ("language", "text", "part"),
    [
        ("en", "Monthly", ", paying monthly"),
        ("en", "Quarterly", ", paying quarterly"),
        ("en", "Semiannually", ", paying semiannually"),
        ("en", "Annually", ", paying annually"),
        ("en", "12 Months", ", paying annually"),
        ("it", "Mensile", ", con cedola mensile"),
        ("it", "Trimestrale", ", con cedola trimestrale"),
        ("it", "Semestrale", ", con cedola semestrale"),
        ("it", "Annuale", ", con cedola annuale"),
        ("en", "Biennial", ""),
        ("en", None, ""),
        ("it", None, ""),
    ],
)
def test_description_frequency(plugin, library, language, text, part):
    """The frequency in words; unknown or absent, the part is left out."""
    start = {"en": "Government bond, issuer Italy", "it": "Titolo di Stato, emittente Italia"}[language]
    description = _synthetic_description(plugin, library, "IT00TESTDE007", language=language, frequenza_cedola=text)
    assert description == f"{start}{part}{MATURES[language]}"


@pytest.mark.parametrize(
    ("month", "english", "italian"),
    [
        (1, "January", "gennaio"),
        (2, "February", "febbraio"),
        (3, "March", "marzo"),
        (4, "April", "aprile"),
        (5, "May", "maggio"),
        (6, "June", "giugno"),
        (7, "July", "luglio"),
        (8, "August", "agosto"),
        (9, "September", "settembre"),
        (10, "October", "ottobre"),
        (11, "November", "novembre"),
        (12, "December", "dicembre"),
    ],
)
@pytest.mark.parametrize("language", LANGUAGES)
def test_description_maturity_month_in_words(plugin, library, month, english, italian, language):
    """The month in words from a fixed table (not the locale), the day without a leading zero."""
    description = _synthetic_description(plugin, library, "IT00TESTDE008", language=language, scadenza=date(2031, month, 5))
    suffix = {"en": f"; matures on 5 {english} 2031.", "it": f"; scade il 5 {italian} 2031."}[language]
    assert description.endswith(suffix), f"{description!r} ends with {suffix!r}"
    assert description.count(";") == 1 and " 05 " not in description


@pytest.mark.parametrize(
    ("day", "english", "italian"),
    [
        (1, "matures on 1 May 2030", "scade il 1\u00ba maggio 2030"),
        (8, "matures on 8 May 2030", "scade l'8 maggio 2030"),
        (11, "matures on 11 May 2030", "scade l'11 maggio 2030"),
        (21, "matures on 21 May 2030", "scade il 21 maggio 2030"),
        (18, "matures on 18 May 2030", "scade il 18 maggio 2030"),
    ],
    ids=["day-1", "day-8", "day-11", "day-21", "day-18"],
)
@pytest.mark.parametrize("language", LANGUAGES)
def test_description_maturity_day(plugin, library, day, english, italian, language):
    """The consultant's Italian day: «il 1º» (U+00BA), «l'8» and «l'11» (ASCII apostrophe), «il D» for every other day
    (21 ends in 1, 18 starts with 8: neither is special); English is the plain day."""
    assert "\u00ba" in italian or day != 1, "barrier: the masculine ordinal indicator, not the degree sign"
    description = _synthetic_description(plugin, library, "IT00TESTDE011", language=language, scadenza=date(2030, 5, day))
    expected = {
        "en": f"Government bond, issuer Italy, paying semiannually; {english}.",
        "it": f"Titolo di Stato, emittente Italia, con cedola semestrale; {italian}.",
    }[language]
    assert description == expected


@pytest.mark.parametrize(
    ("language", "tipologia"),
    [("en", "Italian Government Bonds"), ("it", "Titoli di Stato Italiani"), ("en", None), ("it", None)],
    ids=["en-sovereign", "it-sovereign", "en-no-kind", "it-no-kind"],
)
def test_no_description_when_only_the_kind_is_known(plugin, library, language, tipologia):
    """No issuer, frequency, coupon type or maturity: nothing beyond the kind, so no ``description`` at all (never
    «Bond.» or «Obbligazione.»): a source with nothing to say must not replace the ``legacy`` text."""
    binding = _synthetic(library, "IT00TESTDE012", "btp_ord", language, tipologia=tipologia, emittente=None, frequenza_cedola=None, struttura_bond=None, scadenza=None)
    item = _read_one(plugin, binding)
    assert item.status == EnricherReadStatus.OK, item
    assert not {"issuer_name", "coupon_frequency", "coupon_type", "maturity_date"} & set(item.values), f"barrier: no fact beyond the kind: {sorted(item.values)}"
    assert item.values.get("legal_form") == "bond", "barrier: still a bond, read with its other voices"
    assert "description" not in item.values, f"no description with only the kind known: {item.values.get('description')!r}"


@pytest.mark.parametrize(
    ("language", "tipologia", "expected"),
    [
        ("en", "Italian Government Bonds", "Government bond; matures on 5 June 2030."),
        ("it", "Titoli di Stato Italiani", "Titolo di Stato; scade il 5 giugno 2030."),
        ("en", None, "Bond; matures on 5 June 2030."),
        ("it", None, "Obbligazione; scade il 5 giugno 2030."),
    ],
    ids=["en-sovereign", "it-sovereign", "en-no-kind", "it-no-kind"],
)
def test_description_with_only_the_maturity(plugin, library, language, tipologia, expected):
    """The maturity alone is a fact beyond the kind: the sentence is composed."""
    binding = _synthetic(library, "IT00TESTDE013", "btp_ord", language, tipologia=tipologia, emittente=None, frequenza_cedola=None, struttura_bond=None, scadenza=SYNTHETIC_MATURITY)
    assert _description(_read_one(plugin, binding)) == expected


def test_description_holds_stable_facts_only(plugin, library):
    """Price, yields, both coupons, duration, accrued interest, reference date, outstanding amount and the first day of
    trading change over time (or are no launch date): changing them all leaves the sentence as it was."""
    first = _synthetic(library, "IT00TESTDE009", "btp_valore")
    second = _synthetic(
        library,
        "IT00TESTDE010",
        "btp_valore",
        prezzo=Decimal("87.65"),
        rendimento_lordo=Decimal("6.66"),
        rendimento_netto=Decimal("5.55"),
        cedola_annua=Decimal("7.25"),
        cedola_periodale=Decimal("1.8125"),
        duration_modificata=Decimal("9.99"),
        rateo_lordo=Decimal("0.777"),
        data_prezzo_riferimento=date(2031, 2, 3),
        data_primo_giorno=date(2008, 11, 3),
        outstanding=Decimal("123456789"),
    )
    items = _by_index(list(plugin.read([first, second])), 2)
    assert _stored(items[0].values)["coupon_rate"] != _stored(items[1].values)["coupon_rate"], "barrier: the two sheets differ"
    assert _description(items[0]) == _description(items[1]) == DESCRIPTIONS[("btp_valore", "en")]
    for figure in ("87.65", "6.66", "7.25", "4.5", "1.125", "%", "2008", "2031"):
        assert figure not in _description(items[1]), f"no price, yield, coupon or first day of trading: {figure!r}"


# =============================================================================
# 3. Language (the binding's «language» param; kept together: it may become an instance setting)
# =============================================================================


def test_language_param(plugin):
    """``language`` is a binding param beside ``mic``, ``platform`` and ``codice_fondo`` (C2b), the price plugin's keys.
    The other language cases of this file go through ``_read_recording`` and ``_synthetic``, which put ``language`` in
    the binding's params: the one place to change if it becomes a setting."""
    assert {param["key"] for param in plugin.params_schema} == {"language", "mic", "platform", "codice_fondo"}
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
    texts = {"payout_description", "description"}
    english_stored = {key: value for key, value in _stored(english.values).items() if key not in texts}
    italian_stored = {key: value for key, value in _stored(italian.values).items() if key not in texts}
    assert english_stored == italian_stored, f"{name}: EN and IT differ: {sorted(set(english_stored.items()) ^ set(italian_stored.items()), key=str)}"
    assert english_stored == {key: value for key, value in EXPECTED_BONDS_EN[name].items() if key not in texts}
    assert dict(english.source_dates) == dict(italian.source_dates)
    assert set(_payout(name, "en")) == set(_payout(name, "it")), "barrier: both pages give a payout text, or neither"
    assert _stored(italian.values).get("payout_description") == _payout(name, "it").get("payout_description")
    assert (_description(english), _description(italian)) == (DESCRIPTIONS[(name, "en")], DESCRIPTIONS[(name, "it")]), "C2d: each in its page's language"


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


def test_search_refusal_is_enricher_rate_limited_and_closes_the_session(plugin, library):
    """ENR-3b: the library's refusal (a 403 from the site's firewall) is never an empty result; the session is closed."""
    refusal = bis.RateLimitRaggiunto(WAF_MESSAGE)
    library.answers["lab refused query"] = refusal
    with pytest.raises(EnricherRateLimited) as raised:
        plugin.search("lab refused query")
    assert raised.value.__cause__ is refusal
    assert raised.value.retry_after is None, "the site names no wait"
    assert library.search_calls == [("lab refused query", "it")], "barrier: cerca was called"
    assert len(library.sessions) == 1
    _every_session_closed_once(library)


@pytest.mark.parametrize("error", [bis.RicercaNonDisponibile("search blocked"), bis.ErroreConnessione("timeout")], ids=["unavailable", "connection"])
def test_search_another_failure_is_not_a_refusal(plugin, library, error):
    library.answers["lab failing query"] = error
    with pytest.raises(type(error)) as raised:
        plugin.search("lab failing query")
    assert raised.value is error and not isinstance(raised.value, EnricherRateLimited)
    _every_session_closed_once(library)


# =============================================================================
# 8. Funds (lot C2b): the fund page, by the site's internal code
# =============================================================================


def _fund_binding(code: str = FUND_CODE, **params: Any) -> EnricherBinding:
    return EnricherBinding(FUND_CODE_TYPE, code, params=params)


def _fund_page(code: str, language: str = "en") -> str:
    return f"https://www.borsaitaliana.it/borsa/fondi/dettaglio/{code}.html?lang={language}"


def _synthetic_fund(library: FakeLibrary, code: str, **overrides: Any) -> EnricherBinding:
    """The recorded fund with ``overrides``, offered under ``code``; its ``BI_FUND_CODE`` binding."""
    library.give_fund(code, dataclasses.replace(_fund(), codice=code, **overrides))
    return _fund_binding(code)


def _with_start(text: str | None) -> dict[str, str]:
    """The recorded «Caratteristiche» with «Data di partenza» set to ``text``, or without it (None)."""
    features = {key: value for key, value in _fund().caratteristiche.items() if key != "Data di partenza"}
    return features if text is None else {**features, "Data di partenza": text}


def _read_fund(plugin, library: FakeLibrary, binding: EnricherBinding) -> EnricherReadItem:
    """One fund binding read; barrier: the fund page was asked (today a fund binding is NOT_FOUND with no call)."""
    item = _read_one(plugin, binding)
    assert library.fund_calls == [binding.identifier if binding.identifier_type == FUND_CODE_TYPE else binding.params["codice_fondo"]], f"C2b: a fund binding reads the fund page (ottieni_dati_fondo): fund calls {library.fund_calls}, sheet calls {library.calls}, item {item}"
    assert library.calls == [], f"a fund binding never reads a sheet: {library.calls}"
    return item


def _read_fund_values(plugin, library: FakeLibrary, binding: EnricherBinding) -> dict[str, Any]:
    item = _read_fund(plugin, library, binding)
    assert item.status == EnricherReadStatus.OK, f"the fund page is read: {item}"
    assert all(value is not None for value in item.values.values()), f"a voice the page does not give is absent, never None: {item.values}"
    return _stored(item.values)


def test_fund_recording_rebuilds_as_the_library_types():
    """The recorded fund (green before C2b: it checks the fixture): English envelope, the fund page and the ISIN search
    that finds nothing (the reason for C2b), and a ``DatiFondo`` with the library's real types."""
    recording = _recording(FUND_RECORDING)
    assert set(recording) == {"source", "asset", "version", "recorded_at", "calls"}, f"English envelope keys: {sorted(recording)}"
    assert set(recording["calls"]) == {"ottieni_dati_fondo", "cerca_isin"}
    assert all(call["error"] is None for call in recording["calls"].values())
    assert recording["calls"]["cerca_isin"]["response"] == [], "the site's search does not find the fund by its ISIN"
    fund = _fund()
    assert (fund.codice, fund.isin, fund.nome, fund.valuta) == (FUND_CODE, FUND_ISIN, "Anima Dinamix", "EUR")
    assert isinstance(fund.nav, Decimal) and isinstance(fund.variazione_percentuale, Decimal) and isinstance(fund.data_nav, date)
    assert fund.caratteristiche["Data di partenza"] == "14/03/22"
    assert fund.societa_gestione == {}, "no management company on the only recording: fund_provider is not guessed"


def test_expected_fund_table_is_a_stored_form():
    assert _stored(EXPECTED_FUND) == EXPECTED_FUND
    assert set(EXPECTED_FUND) == FUND_VOICES


def test_the_fund_reader_is_imported_at_module_level():
    """``ottieni_dati_fondo`` is a module-level name of the plugin, as ``ottieni_scheda``: the fixtures replace it there,
    so no fund read of this file reaches borsaitaliana.it."""
    module = importlib.import_module(PLUGIN_MODULE)
    assert getattr(module, "ottieni_dati_fondo", None) is bis.ottieni_dati_fondo, "C2b: `from borsa_italiana_scraping import ottieni_dati_fondo` in the plugin"


def test_binding_param_codice_fondo(plugin):
    param = _param(plugin, "codice_fondo")
    assert param["type"] == "string", param
    assert not param.get("required", False), f"codice_fondo is optional: {param}"
    assert param.get("default") in (None, ""), f"codice_fondo has no default: {param}"
    assert param.get("x-i18n-key") == "enrichers.borsa_italiana.params.codice_fondo", param


@pytest.mark.parametrize(
    ("binding", "url"),
    [
        (_fund_binding(), _fund_page(FUND_CODE)),
        (_fund_binding(language="it"), _fund_page(FUND_CODE, "it")),
        (_isin(FUND_ISIN, codice_fondo=FUND_CODE), _fund_page(FUND_CODE)),
        (_isin(FUND_ISIN, codice_fondo=FUND_CODE, language="it"), _fund_page(FUND_CODE, "it")),
    ],
    ids=["fund-code", "fund-code-it", "isin-codice-fondo", "isin-codice-fondo-it"],
)
def test_page_url_of_a_fund(plugin, binding, url):
    """The price plugin's rule (``get_asset_url``): the fund-detail page of the internal code, in the binding's language."""
    assert plugin.page_url(binding) == url


# --- read ---------------------------------------------------------------------


def test_read_a_fund_code_binding(plugin, library):
    library.give_fund(FUND_CODE, _fund())
    item = _read_fund(plugin, library, _fund_binding())
    assert item.status == EnricherReadStatus.OK, item
    assert _stored(item.values) == EXPECTED_FUND
    assert len(library.sessions) == 1 and library.fund_call_sessions == library.sessions, "the read's one session handed to the fund call"
    _every_session_closed_once(library)


def test_read_an_isin_binding_with_codice_fondo(plugin, library):
    """The price plugin's binding shape: the ISIN, the internal code in ``codice_fondo``."""
    library.give_fund(FUND_CODE, _fund())
    assert _read_fund_values(plugin, library, _isin(FUND_ISIN, codice_fondo=FUND_CODE)) == EXPECTED_FUND


@pytest.mark.parametrize("params", [{}, {"codice_fondo": ""}, {"codice_fondo": None}], ids=["no-codice-fondo", "empty", "none"])
def test_read_an_isin_binding_without_a_fund_code_stays_on_the_sheet(plugin, library, params):
    """Guard (green before C2b): an ISIN binding without a fund code reads the sheet, never the fund page."""
    isin = _give_recording(library, "btp_valore")
    item = _read_one(plugin, _isin(isin, **params))
    assert item.status == EnricherReadStatus.OK
    assert library.isins_called == [isin] and library.fund_calls == []


@pytest.mark.parametrize("voice", ["ter", "fund_size", "fund_provider", "description", "sector", "legal_form"])
def test_fund_voices_not_written(plugin, library, voice):
    """«Gestione» is the management fee, only a part of the TER (C2e: written as ``management_fee``, never ``ter``);
    «Patrimonio del fondo» has no unit; no management company is guessed; no fund sentence is approved; risk grade and
    category have no catalogue voice."""
    library.give_fund(FUND_CODE, _fund())
    values = _read_fund_values(plugin, library, _fund_binding())
    assert voice not in values, f"{voice} is not written for a fund: {values}"
    assert set(values) <= FUND_VOICES, f"only the declared fund voices: {sorted(values)}"


def test_a_management_company_on_the_page_writes_no_fund_provider(plugin, library):
    binding = _synthetic_fund(library, "1FTESTSG0001", societa_gestione={"Denominazione": "Anima SGR S.p.A."})
    values = _read_fund_values(plugin, library, binding)
    assert values == EXPECTED_FUND, f"fund_provider is not guessed: {values}"


@pytest.mark.parametrize(
    ("text", "stored"),
    [("14/03/22", "2022-03-14"), ("01/12/99", "1999-12-01"), ("01/01/50", "1950-01-01"), ("14/03/2022", "2022-03-14"), ("05/07/1998", "1998-07-05")],
    ids=["two-digit-20yy", "two-digit-19yy", "two-digit-mid-range-19yy", "four-digit", "four-digit-1900s"],
)
def test_fund_inception_date(plugin, library, text, stored):
    """«Data di partenza», day/month/year. Two-digit years pivot on today's year (20yy up to its two digits, else 19yy):
    the pivot's edge moves with the calendar, so only years far from it are pinned. «50» → 1950 holds until 2049 and
    tells the contract's pivot from ``strptime``'s fixed one (``%y``: 00–68 → 20yy), which gives 2050."""
    values = _read_fund_values(plugin, library, _synthetic_fund(library, "1FTESTID0001", caratteristiche=_with_start(text)))
    assert values.get("inception_date") == stored, f"{text!r}: {values}"


@pytest.mark.parametrize("text", [None, "", "N.D.", "N.A.", "31/02/22", "14/03", "not a date"], ids=["missing", "empty", "nd", "na", "no-such-day", "no-year", "text"])
def test_fund_inception_date_absent_when_unparsable(plugin, library, text):
    values = _read_fund_values(plugin, library, _synthetic_fund(library, "1FTESTID0002", caratteristiche=_with_start(text)))
    assert "inception_date" not in values, f"{text!r}: {values}"
    assert values == {"fund_currency": "EUR", "management_fee": "0.004"}, "the currency and the fee still come"


def _with_fee(text: str | None) -> dict[str, str]:
    """The recorded «Costi» with «Gestione» set to ``text``, or without it (None)."""
    costs = {key: value for key, value in _fund().costi.items() if key != "Gestione"}
    return costs if text is None else {**costs, "Gestione": text}


@pytest.mark.parametrize(
    ("text", "stored"),
    [("0.4", "0.004"), ("0,40", "0.004"), ("1.5", "0.015"), ("2", "0.02"), (" 0.4 ", "0.004"), ("0.4%", "0.004")],
    ids=["recorded", "comma", "one-and-a-half", "integer", "spaces", "percent-sign"],
)
def test_fund_management_fee(plugin, library, text, stored):
    """C2e (developer, «voce sua»): «Gestione», a percentage per year (the prospectus: «commissione di gestione …
    0,40% su base annua»), stored as a fraction in ``management_fee``; never the TER."""
    values = _read_fund_values(plugin, library, _synthetic_fund(library, "1FTESTMF0001", costi=_with_fee(text)))
    assert values.get("management_fee") == stored, f"{text!r}: {values}"
    assert "ter" not in values, "the management fee is only a part of the TER: never written as ter"


@pytest.mark.parametrize("text", [None, "", "N.D.", "N.A.", "abc", "-0.4"], ids=["missing", "empty", "nd", "na", "text", "negative"])
def test_fund_management_fee_absent_when_unreadable(plugin, library, text):
    values = _read_fund_values(plugin, library, _synthetic_fund(library, "1FTESTMF0002", costi=_with_fee(text)))
    assert "management_fee" not in values, f"{text!r}: {values}"
    assert values == {"fund_currency": "EUR", "inception_date": "2022-03-14"}, "the other fund voices still come"


def test_fund_currency_from_the_page(plugin, library):
    values = _read_fund_values(plugin, library, _synthetic_fund(library, "1FTESTCU0001", valuta="USD"))
    assert values == {**EXPECTED_FUND, "fund_currency": "USD"}


def test_fund_without_a_currency_has_none(plugin, library):
    """An empty ``valuta`` leaves the voice out, never the price plugin's «EUR» default."""
    values = _read_fund_values(plugin, library, _synthetic_fund(library, "1FTESTCU0002", valuta=""))
    assert values == {"inception_date": "2022-03-14", "management_fee": "0.004"}


@pytest.mark.parametrize("error_class", [bis.StrumentoNonTrovato, bis.StrumentoNonRisolto, bis.DatiNonDisponibili])
@pytest.mark.parametrize("by_isin", [False, True], ids=["fund-code", "isin-codice-fondo"])
def test_fund_not_found_errors(plugin, library, error_class, by_isin):
    """A fund page the site does not give, or gives without data, is not found (unlike ``DatiNonDisponibili`` on the
    sheet path, a ``SOURCE_ERROR``)."""
    code = library.give_fund("1FTESTNF0001", error_class("not found"))
    binding = _isin(FUND_ISIN, codice_fondo=code) if by_isin else _fund_binding(code)
    item = _read_fund(plugin, library, binding)
    assert item.status == EnricherReadStatus.NOT_FOUND and item.error_code is None, item


@pytest.mark.parametrize("error", [bis.ErroreConnessione("timeout"), ValueError("unexpected page layout")], ids=["connection", "other"])
def test_fund_read_error_is_an_error_item_and_the_next_is_read(plugin, library, error):
    failing = library.give_fund("1FTESTER0001", error)
    valore = _give_recording(library, "btp_valore")
    items = _by_index(list(plugin.read([_fund_binding(failing), _isin(valore)])), 2)
    assert library.fund_calls == [failing], f"C2b: the fund page was asked: {library.fund_calls}"
    assert items[0].status == EnricherReadStatus.ERROR and items[0].error_code == SOURCE_ERROR, items[0]
    assert items[1].status == EnricherReadStatus.OK
    assert library.isins_called == [valore]
    _every_session_closed_once(library)


def test_fund_rate_limited_defers_every_remaining_binding(plugin, library):
    ord_ = _give_recording(library, "btp_ord")
    refused = library.give_fund("1FTESTRL0001", bis.RateLimitRaggiunto(WAF_MESSAGE))
    # never offered: a call for either fails the test
    bindings = [_isin(ord_), _fund_binding(refused), _fund_binding("1FTESTRL0002"), _isin("IT00TESTRL005")]

    items = _by_index(list(plugin.read(bindings)), len(bindings))

    assert items[0].status == EnricherReadStatus.OK
    for index in (1, 2, 3):
        assert items[index].status == EnricherReadStatus.ERROR and items[index].error_code == RATE_LIMITED, f"binding {index}: {items[index]}"
    assert library.isins_called == [ord_] and library.fund_calls == [refused], "no call after the refusal"
    _every_session_closed_once(library)


def test_a_sheet_refusal_defers_a_fund_binding(plugin, library):
    refused = library.give("IT00TESTRL006", bis.RateLimitRaggiunto(WAF_MESSAGE))
    items = _by_index(list(plugin.read([_isin(refused), _fund_binding()])), 2)  # the fund is never offered
    assert items[1].status == EnricherReadStatus.ERROR and items[1].error_code == RATE_LIMITED, items[1]
    assert library.fund_calls == []


def test_one_session_for_sheets_and_funds(plugin, library):
    """A read mixing sheets and funds: one session, handed to every call of either kind, closed once."""
    library.give_fund(FUND_CODE, _fund())
    valore = _give_recording(library, "btp_valore")
    bindings = [_isin(valore), _fund_binding(), _isin(FUND_ISIN, codice_fondo=FUND_CODE)]

    items = _by_index(list(plugin.read(bindings)), 3)

    assert [items[i].status for i in range(3)] == [EnricherReadStatus.OK] * 3, items
    assert _stored(items[1].values) == _stored(items[2].values) == EXPECTED_FUND
    assert library.isins_called == [valore] and library.fund_calls == [FUND_CODE, FUND_CODE]
    assert len(library.sessions) == 1, f"one session for the read: {library.sessions}"
    assert library.call_sessions == [library.sessions[0]] and library.fund_call_sessions == [library.sessions[0]] * 2
    _every_session_closed_once(library)


# --- recognize ----------------------------------------------------------------


def test_recognize_a_fund_code(plugin, library):
    """Found, its name and page, and its ISIN: a strong identifier that carries the cascade to the other enrichers."""
    fund = _fund()
    library.give_fund(FUND_CODE, fund)
    recognition = plugin.recognize(_fund_binding())
    assert library.fund_calls == [FUND_CODE], f"C2b: recognize reads the fund page: {library.fund_calls}"
    assert recognition == EnricherRecognition(found=True, name="Anima Dinamix", page_url=fund.url, identifiers={"ISIN": FUND_ISIN})
    assert library.calls == []


def test_recognize_a_fund_without_an_isin(plugin, library):
    binding = _synthetic_fund(library, "1FTESTRC0001", isin=None)
    recognition = plugin.recognize(binding)
    assert library.fund_calls == ["1FTESTRC0001"], f"C2b: recognize reads the fund page: {library.fund_calls}"
    assert recognition.found is True and recognition.identifiers == {}, recognition


def test_recognize_a_fund_without_a_page_url_uses_the_plugins(plugin, library):
    binding = _synthetic_fund(library, "1FTESTRC0002", url="")
    recognition = plugin.recognize(binding)
    assert recognition.found is True, recognition
    assert recognition.page_url == plugin.page_url(binding) == _fund_page("1FTESTRC0002")


def test_recognize_an_isin_binding_with_codice_fondo(plugin, library):
    """The ISIN binding of the price plugin's shape reads the fund page too (its ``identifiers`` are not pinned)."""
    fund = _fund()
    library.give_fund(FUND_CODE, fund)
    recognition = plugin.recognize(_isin(FUND_ISIN, codice_fondo=FUND_CODE))
    assert library.fund_calls == [FUND_CODE] and library.calls == [], f"the fund page, not the sheet: {library.fund_calls} {library.calls}"
    assert (recognition.found, recognition.name, recognition.page_url) == (True, "Anima Dinamix", fund.url)


@pytest.mark.parametrize("error_class", [bis.StrumentoNonTrovato, bis.StrumentoNonRisolto, bis.DatiNonDisponibili])
def test_recognize_a_fund_not_found(plugin, library, error_class):
    code = library.give_fund("1FTESTNF0002", error_class("not found"))
    assert plugin.recognize(_fund_binding(code)).found is False
    assert library.fund_calls == [code], f"C2b: the fund page was asked: {library.fund_calls}"


def test_recognize_a_fund_rate_limited_raises(plugin, library):
    code = library.give_fund("1FTESTRL0003", bis.RateLimitRaggiunto(WAF_MESSAGE))
    with pytest.raises(Exception) as raised:
        plugin.recognize(_fund_binding(code))
    assert rate_limited_from_exception(raised.value, CODE) is not None, f"the core must read it as a refusal: {raised.value!r}"


def test_recognize_a_fund_other_error_raises(plugin, library):
    code = library.give_fund("1FTESTRE0001", bis.ErroreConnessione("timeout"))
    with pytest.raises(Exception) as raised:
        plugin.recognize(_fund_binding(code))
    assert rate_limited_from_exception(raised.value, CODE) is None, f"not a refusal: {raised.value!r}"


# =============================================================================
# C5: one pace for every call of the plugin, whatever read it comes from
# =============================================================================


class FakePace:
    """The module's ``_PACER`` replaced by one on a fake clock that only moves when it sleeps: no test ever waits, and
    the waits are recorded. ``interval`` is the plugin's own."""

    def __init__(self, interval: float) -> None:
        self.interval = interval
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
    """Every test of this file runs on the fake pace: the module must hold its ``_PACER`` (C5)."""
    module = importlib.import_module(PLUGIN_MODULE)
    real = module._PACER
    assert isinstance(real, Pacer) and real.interval_seconds > 0, "the plugin paces its calls with a module-level Pacer"
    fake = FakePace(real.interval_seconds)
    monkeypatch.setattr(module, "_PACER", Pacer(real.interval_seconds, clock=fake.clock, sleep=fake.sleep), raising=True)
    return fake


def test_two_reads_share_one_pace(bi, library, pace):
    """Two reads, each with its own library session (as two requests at once): the second waits the plugin's interval
    before its first call, though the library paces only inside one session."""
    first, second = bi.BorsaItalianaEnricher(), bi.BorsaItalianaEnricher()
    isin = _give_recording(library, "btp_valore")
    assert list(first.read([_isin(isin)]))[0].status == EnricherReadStatus.OK
    assert pace.slept == [], "the first call does not wait"
    assert list(second.read([_isin(isin)]))[0].status == EnricherReadStatus.OK
    assert pace.slept == [pace.interval], f"the second read waited the interval: {pace.slept}"


def test_search_is_paced_with_the_reads(bi, library, pace, plugin):
    isin = _give_recording(library, "btp_valore")
    list(plugin.read([_isin(isin)]))
    library.answers["btp"] = []
    plugin.search("btp")
    assert pace.slept == [pace.interval], f"search and read share the pace: {pace.slept}"


# =============================================================================
# 9. The company profile of a share (lot BI-PROF)
# =============================================================================

PROFILE_RECORDING = "enel_profile"
ENEL_ISIN = "IT0003128367"
#: The «last update» of both recorded profile pages.
PROFILE_DATE = date(2026, 10, 23)
#: The recorded descriptions begin so (a barrier on the recording, not a rebuilt text).
PROFILE_STARTS = {"en": "Enel S.p.A. is Italian No. 1 producer", "it": "Enel S.p.A. è il primo produttore"}
#: A registered office no country helper knows.
UNKNOWN_COUNTRY = "Neverland"


@dataclasses.dataclass
class _AddressStandIn:
    """``IndirizzoSocieta`` for a library that does not have it: the same field names."""

    ragione_sociale: str | None = None
    via: str | None = None
    cap: str | None = None
    comune: str | None = None
    paese: str | None = None


@dataclasses.dataclass
class _ContactsStandIn:
    """``ContattiSocieta`` for a library that does not have it: the same field names."""

    telefono: str | None = None
    email: str | None = None
    sito_web: str | None = None


@dataclasses.dataclass
class _DatumStandIn:
    """``DatoSocietario`` for a library that does not have it: the same field names."""

    voce: str
    valori: dict[int, Any] = dataclasses.field(default_factory=dict)


@dataclasses.dataclass
class _ProfileStandIn:
    """``ProfiloSocieta`` for a library that does not have it: the same field names, the nested rows as recorded."""

    isin: str
    mic: str
    descrizione: str | None = None
    dirigenti: list[Any] = dataclasses.field(default_factory=list)
    anni_disponibili: list[int] = dataclasses.field(default_factory=list)
    dati_principali: list[Any] = dataclasses.field(default_factory=list)
    azionisti: list[Any] = dataclasses.field(default_factory=list)
    indirizzo: Any = None
    contatti: Any = None
    fonte: str | None = None
    ultimo_aggiornamento: date | None = None
    url_pagina: str | None = None


_PROFILE_FIELDS = tuple(field.name for field in dataclasses.fields(_ProfileStandIn))
_ADDRESS_FIELDS = tuple(field.name for field in dataclasses.fields(_AddressStandIn))
_CONTACTS_FIELDS = tuple(field.name for field in dataclasses.fields(_ContactsStandIn))
_DATUM_FIELDS = tuple(field.name for field in dataclasses.fields(_DatumStandIn))
#: Enel's website on both pages, and the two figures of 2025 in stored form («78057», «5617» in EUR millions).
ENEL_WEBSITE = "https://www.enel.com/investors/overview"
ENEL_FIGURES = {"revenue": {"amount": "78057000000", "currency": "EUR"}, "net_income": {"amount": "5617000000", "currency": "EUR"}}
#: The end of Enel's fiscal year 2025, which dates both figures.
FISCAL_YEAR_END = date(2025, 12, 31)


def _profile_response(language: str) -> dict[str, Any]:
    response = _recording(PROFILE_RECORDING)["calls"][f"profilo_{language}"]["response"]
    assert response is not None, f"barrier: the {language} profile page is recorded"
    assert set(response) == set(_PROFILE_FIELDS), f"the recording has ProfiloSocieta's fields: {sorted(set(response) ^ set(_PROFILE_FIELDS))}"
    return response


def _cell(value: str | None) -> Decimal | date | str | None:
    """A recorded value of ``DatoSocietario.valori``: a number, a date, or a text («IFRS»)."""
    if value is None:
        return None
    with contextlib.suppress(ArithmeticError):  # parsing probe: not a number
        return Decimal(value)
    with contextlib.suppress(ValueError):  # parsing probe: not a date
        return date.fromisoformat(value)
    return value


def _profile(language: str = "en", **overrides: Any) -> Any:
    """The recorded profile page of Enel in ``language``: the library's ``ProfiloSocieta`` when the installed library has
    it (with its real nested types), else the stand-in; ``overrides`` replace fields."""
    response = _profile_response(language)
    day = date.fromisoformat(response["ultimo_aggiornamento"]) if response["ultimo_aggiornamento"] else None
    address = response["indirizzo"]
    if LIBRARY_HAS_PROFILE:
        profile = bis.ProfiloSocieta(
            isin=response["isin"],
            mic=response["mic"],
            descrizione=response["descrizione"],
            dirigenti=[bis.Dirigente(**row) for row in response["dirigenti"]],
            anni_disponibili=list(response["anni_disponibili"]),
            dati_principali=[bis.DatoSocietario(voce=row["voce"], valori={int(year): _cell(value) for year, value in row["valori"].items()}) for row in response["dati_principali"]],
            azionisti=[bis.Azionista(nominativo=row["nominativo"], percentuale=None if row["percentuale"] is None else Decimal(row["percentuale"])) for row in response["azionisti"]],
            indirizzo=bis.IndirizzoSocieta(**address) if address is not None else None,
            contatti=bis.ContattiSocieta(**response["contatti"]),
            fonte=response["fonte"],
            ultimo_aggiornamento=day,
            url_pagina=response["url_pagina"],
        )
    else:
        profile = _ProfileStandIn(
            **{
                **response,
                "dati_principali": [_datum(row["voce"], {int(year): _cell(value) for year, value in row["valori"].items()}) for row in response["dati_principali"]],
                "indirizzo": _AddressStandIn(**address) if address is not None else None,
                "contatti": _ContactsStandIn(**response["contatti"]),
                "ultimo_aggiornamento": day,
            }
        )
    return dataclasses.replace(profile, **overrides)


def _datum(label: str, values: dict[int, Any]) -> Any:
    """One row of the «main data» table: the library's ``DatoSocietario``, else the stand-in."""
    return bis.DatoSocietario(voce=label, valori=values) if LIBRARY_HAS_PROFILE else _DatumStandIn(voce=label, valori=values)


def _with_website(profile: Any, website: str | None) -> Any:
    return dataclasses.replace(profile, contatti=dataclasses.replace(profile.contatti, sito_web=website))


def _with_country(profile: Any, country: str | None) -> Any:
    return dataclasses.replace(profile, indirizzo=dataclasses.replace(profile.indirizzo, paese=country))


def _enel(library: FakeLibrary, language: str = "en", profile: Any = None, **params: Any) -> EnricherBinding:
    """Enel's recorded sheet (the English page, offered for ``language``) and, when given, its profile."""
    library.give(ENEL_ISIN, _sheet("enel"), language)
    if profile is not None:
        library.give_profile(ENEL_ISIN, profile, language)
    return _isin(ENEL_ISIN, **({} if language == "en" else {"language": language}), **params)


def _warnings_naming(events: list[dict[str, Any]], text: str) -> list[dict[str, Any]]:
    return [event for event in _log_lines_naming(events, text) if event.get("log_level") == "warning"]


@pytest.mark.parametrize("language", LANGUAGES)
def test_profile_recording_rebuilds_as_the_library_types(language):
    """The recording has ``ProfiloSocieta``'s fields; the stand-in has the library's, when the library has them."""
    if LIBRARY_HAS_PROFILE:
        assert _PROFILE_FIELDS == tuple(field.name for field in dataclasses.fields(bis.ProfiloSocieta)), "the stand-in has the library's fields"
        assert _ADDRESS_FIELDS == tuple(field.name for field in dataclasses.fields(bis.IndirizzoSocieta)), "the stand-in address has the library's fields"
        assert _CONTACTS_FIELDS == tuple(field.name for field in dataclasses.fields(bis.ContattiSocieta)), "the stand-in contacts have the library's fields"
        assert _DATUM_FIELDS == tuple(field.name for field in dataclasses.fields(bis.DatoSocietario)), "the stand-in row has the library's fields"
    profile = _profile(language)
    assert (profile.isin, profile.mic, profile.ultimo_aggiornamento) == (ENEL_ISIN, "MTAA", PROFILE_DATE)
    assert profile.descrizione.startswith(PROFILE_STARTS[language]), profile.descrizione[:60]
    assert profile.indirizzo.paese == "Italy", "the registered office, «Italy» on both pages"
    assert profile.contatti.sito_web == ENEL_WEBSITE, "barrier: the recorded website, already a web address"
    rows = {row.voce: row.valori for row in profile.dati_principali}
    unit, end = ("Currency & Unit", "Fiscal year end") if language == "en" else ("Valuta e unità di misura", "Chiusura esercizio fiscale")
    assert rows[unit][2025] in ("EUR - millions", "EUR - milioni") and rows[end][2025] == FISCAL_YEAR_END, "barrier: the 2025 unit and fiscal year end"
    if LIBRARY_HAS_PROFILE:
        assert isinstance(profile.azionisti[0].percentuale, Decimal) and isinstance(next(iter(profile.dati_principali[0].valori)), int)
    sheet = _sheet("enel")
    assert sheet.isin == ENEL_ISIN and sheet.tipo == "azione" and "-MTAA.html" in sheet.url_pagina, "barrier: the sheet beside it is Enel's share on MTAA"


@pytest.mark.parametrize("language", LANGUAGES)
def test_profile_voices_of_a_share(plugin, library, language):
    """Enel: the sheet's voices plus the profile page's description (as written, in the binding's language), country
    (ITA) and website, dated by the page's last update, and the revenue and net income of 2025 scaled from millions,
    dated by the end of that fiscal year; one profile call, on the sheet's MIC."""
    item = _read_one(plugin, _enel(library, language, _profile(language)))

    assert item.status == EnricherReadStatus.OK, item
    description = _profile_response(language)["descrizione"].strip()
    expected = {**EXPECTED_OTHERS["enel"], "description": description, "issuer_country": "ITA", "website": ENEL_WEBSITE, **ENEL_FIGURES}
    assert _stored(item.values) == expected
    assert _stored(item.values)["description"].startswith(PROFILE_STARTS[language])
    expected_dates = {**dict.fromkeys(PAGE_VOICES, PROFILE_DATE), **dict.fromkeys(FISCAL_VOICES, FISCAL_YEAR_END)}
    assert dict(item.source_dates) == expected_dates, f"the page's voices dated by its update, the figures by their fiscal year end: {dict(item.source_dates)}"
    assert item.source_date is None
    assert library.calls == [(ENEL_ISIN, None, language, None)], "barrier: one sheet call"
    assert library.profile_calls == [(ENEL_ISIN, "MTAA", language)], f"one profile call, the sheet's MIC, the binding's language: {library.profile_calls}"


@pytest.mark.parametrize(
    ("params", "url", "mic"),
    [
        ({"mic": "etlx"}, None, "ETLX"),
        ({}, None, "MTAA"),
        ({}, "https://www.borsaitaliana.it/borsa/azioni/scheda/IT0003128367-xmil.html", "XMIL"),
        ({}, "", None),
        ({}, "https://www.borsaitaliana.it/borsa/azioni/scheda.html", None),
    ],
    ids=["binding-mic-wins", "url-mic", "url-mic-upper", "no-url", "url-without-mic"],
)
def test_profile_mic_from_the_binding_else_the_sheet_url(plugin, library, params, url, mic):
    """The binding's ``mic`` (upper case) wins over the sheet's URL; else the MIC in ``…/<ISIN>-<MIC>.html``; else
    None (pinned as the plugin does: the library is asked with no market)."""
    sheet = _sheet("enel") if url is None else dataclasses.replace(_sheet("enel"), url_pagina=url)
    assert url is not None or "-MTAA.html" in sheet.url_pagina, "barrier: the recorded URL carries MTAA"
    library.give(ENEL_ISIN, sheet)
    library.give_profile(ENEL_ISIN, _profile())

    item = _read_one(plugin, _isin(ENEL_ISIN, **params))

    assert item.status == EnricherReadStatus.OK and "issuer_country" in item.values, item
    assert library.profile_calls == [(ENEL_ISIN, mic, "en")], library.profile_calls


@pytest.mark.parametrize(
    ("keys", "asked"),
    [
        (None, True),
        (["sector"], False),
        (["sector", "legal_form"], False),
        (["description"], True),
        (["issuer_country"], True),
        (["sector", "description"], True),
        (["website"], True),
        (["revenue"], True),
        (["net_income"], True),
    ],
    ids=["every-voice", "sector", "sheet-voices", "description", "issuer-country", "sector-and-description", "website", "revenue", "net-income"],
)
def test_the_profile_is_read_only_when_one_of_its_voices_is_asked(plugin, library, keys, asked):
    """One more request per share only when it can give something asked: ``keys`` None, or naming a profile voice."""
    binding = _enel(library, profile=_profile())

    items = list(plugin.read([binding], keys=keys))

    assert len(items) == 1 and items[0].status == EnricherReadStatus.OK, items
    assert library.calls == [(ENEL_ISIN, None, "en", None)], "barrier: the sheet is read in every case"
    assert len(library.profile_calls) == (1 if asked else 0), f"keys {keys}: profile calls {library.profile_calls}"
    if asked:
        assert PROFILE_VOICES <= set(items[0].values), items[0].values
    else:
        assert _stored(items[0].values) == EXPECTED_OTHERS["enel"] and dict(items[0].source_dates) == {}, items[0]


def test_bonds_funds_and_etfs_never_ask_the_profile(plugin, library):
    """Only a share (``tipo == "azione"``) has a company profile: a bond, an ETF, another sheet and a fund never ask it."""
    library.give_fund(FUND_CODE, _fund())
    bindings = [
        _isin(_give_recording(library, "btp_valore")),
        _isin(_give_recording(library, "bond_corp")),
        _isin(_give_recording(library, "swda")),
        _synthetic(library, "IT00TESTPR001", base="enel", tipo="altro"),
        _fund_binding(),
    ]

    items = _by_index(list(plugin.read(bindings)), len(bindings))

    assert all(item.status == EnricherReadStatus.OK for item in items.values()), items
    assert len(library.calls) == 4 and library.fund_calls == [FUND_CODE], "barrier: every page was read"
    assert library.profile_calls == [], f"no profile for a non-share: {library.profile_calls}"


def test_a_library_without_the_profile_reader_keeps_the_sheet_voices(bi, plugin, library, monkeypatch):
    """The plugin's module-level ``ottieni_profilo_societa`` None (a library older than the lot): the sheet alone."""
    monkeypatch.setattr(bi, "ottieni_profilo_societa", None, raising=True)
    item = _read_one(plugin, _enel(library, profile=_profile()))
    assert item.status == EnricherReadStatus.OK, item
    assert _stored(item.values) == EXPECTED_OTHERS["enel"] and dict(item.source_dates) == {}
    assert library.profile_calls == []


@pytest.mark.parametrize("error_class", [bis.StrumentoNonTrovato, bis.StrumentoNonRisolto])
def test_a_share_without_a_profile_page_keeps_the_sheet_voices(plugin, library, error_class):
    """No profile page for this share («not found», «not resolved» too): OK with the sheet's voices, no log line."""
    binding = _enel(library, profile=error_class(f"no profile page for {ENEL_ISIN}"))
    with capture_logs() as events:
        item = _read_one(plugin, binding)
    assert item.status == EnricherReadStatus.OK, item
    assert _stored(item.values) == EXPECTED_OTHERS["enel"] and dict(item.source_dates) == {}
    assert len(library.profile_calls) == 1, "barrier: the profile was asked"
    assert _warnings_naming(events, ENEL_ISIN) == [], f"a missing page is no failure: {events}"


@pytest.mark.parametrize("error", [bis.ErroreConnessione("timeout"), bis.DatiNonDisponibili("no data"), ValueError("unexpected page layout")], ids=["connection", "no-data", "other"])
def test_a_failing_profile_keeps_the_sheet_voices_with_one_log_line(plugin, library, error):
    """Any other failure of the profile call: OK with the sheet's voices, one warning naming the share; the next binding
    is read (``DatiNonDisponibili`` included, which is ``SOURCE_ERROR`` on the sheet's path)."""
    share = _enel(library, profile=error)
    bond = _isin(_give_recording(library, "btp_ord"))
    with capture_logs() as events:
        items = _by_index(list(plugin.read([share, bond])), 2)
    assert items[0].status == EnricherReadStatus.OK, items[0]
    assert _stored(items[0].values) == EXPECTED_OTHERS["enel"] and dict(items[0].source_dates) == {}
    assert items[1].status == EnricherReadStatus.OK, "the next binding is read"
    assert len(_warnings_naming(events, ENEL_ISIN)) == 1, f"one warning names the share: {events}"


def test_a_profile_refusal_defers_every_remaining_binding(plugin, library):
    """``RateLimitRaggiunto`` on the profile: that share ``ERROR`` ``RATE_LIMITED``, and every binding after it (a sheet,
    a fund) the same, without a call."""
    ordinary = _isin(_give_recording(library, "btp_ord"))
    share = _enel(library, profile=bis.RateLimitRaggiunto(WAF_MESSAGE))
    # never offered: a call for either fails the test
    bindings = [ordinary, share, _isin("IT00TESTPR002"), _fund_binding("1FTESTPR003")]

    items = _by_index(list(plugin.read(bindings)), len(bindings))

    assert items[0].status == EnricherReadStatus.OK
    for index in (1, 2, 3):
        assert items[index].status == EnricherReadStatus.ERROR and items[index].error_code == RATE_LIMITED, f"binding {index}: {items[index]}"
    assert library.isins_called == [_sheet("btp_ord").isin, ENEL_ISIN] and library.fund_calls == [], "no call after the refusal"
    assert library.profile_calls == [(ENEL_ISIN, "MTAA", "en")]
    _every_session_closed_once(library)


def test_an_unknown_country_leaves_the_voice_out_with_one_log_line(plugin, library):
    """A registered office no helper translates: no ``issuer_country`` (never a guess), one log line naming it; the
    other voices stay, with their dates."""
    with pytest.raises(ValueError):
        normalize_country_to_iso3(UNKNOWN_COUNTRY)
    binding = _enel(library, profile=_with_country(_profile(), UNKNOWN_COUNTRY))
    with capture_logs() as events:
        item = _read_one(plugin, binding)
    assert item.status == EnricherReadStatus.OK, item
    assert "issuer_country" not in item.values and "description" in item.values, item.values
    assert dict(item.source_dates) == {"description": PROFILE_DATE, "website": PROFILE_DATE, **dict.fromkeys(FISCAL_VOICES, FISCAL_YEAR_END)}
    assert len(_log_lines_naming(events, UNKNOWN_COUNTRY)) == 1, f"one log line names the country: {events}"


_NO_CONTACTS = {"contatti": None}
_NO_MAIN_DATA = {"dati_principali": []}


@pytest.mark.parametrize(
    ("overrides", "voices"),
    [
        ({"indirizzo": None}, PROFILE_VOICES - {"issuer_country"}),
        ({"descrizione": "  "}, PROFILE_VOICES - {"description"}),
        (_NO_CONTACTS, PROFILE_VOICES - {"website"}),
        (_NO_MAIN_DATA, PAGE_VOICES),
        ({"descrizione": None, "indirizzo": None, **_NO_CONTACTS, **_NO_MAIN_DATA}, frozenset()),
    ],
    ids=["no-address", "blank-description", "no-contacts", "no-main-data", "nothing"],
)
def test_a_profile_without_a_voice_gives_the_others_silently(plugin, library, overrides, voices):
    """A page without an address, a description, contacts or a «main data» table gives what it has, with no log line;
    a page with none of them, the sheet's voices only."""
    with capture_logs() as events:
        item = _read_one(plugin, _enel(library, profile=_profile(**overrides)))
    assert item.status == EnricherReadStatus.OK, item
    assert set(item.values) & PROFILE_VOICES == voices, item.values
    assert dict(item.source_dates) == {key: FISCAL_YEAR_END if key in FISCAL_VOICES else PROFILE_DATE for key in voices}
    assert _warnings_naming(events, ENEL_ISIN) == [], events


def test_a_profile_without_an_update_date_dates_only_the_figures(plugin, library):
    """No «last update»: the page's voices undated; the figures keep the end of their fiscal year, their own date."""
    item = _read_one(plugin, _enel(library, profile=_profile(ultimo_aggiornamento=None)))
    assert item.status == EnricherReadStatus.OK and PROFILE_VOICES <= set(item.values), item
    assert dict(item.source_dates) == dict.fromkeys(FISCAL_VOICES, FISCAL_YEAR_END)


def test_the_profile_uses_the_read_session_and_its_pace(plugin, library, pace):
    """The profile call gets the read's one session (the sheet's, the same object), still open; it is paced as any
    other call of the plugin; the session is closed once after."""
    item = _read_one(plugin, _enel(library, profile=_profile()))
    assert item.status == EnricherReadStatus.OK, item
    assert len(library.sessions) == 1, "barrier: one session for the read"
    assert library.profile_call_sessions == [library.sessions[0]] and library.call_sessions == [library.sessions[0]]
    assert library.profile_call_sessions[0] is library.call_sessions[0]
    assert pace.slept == [pace.interval], f"the profile call waits the plugin's interval after the sheet's: {pace.slept}"
    _every_session_closed_once(library)


@pytest.mark.parametrize("has_reader", [True, False], ids=["library-with-reader", "library-without-reader"])
def test_stock_voices_declared_by_the_installed_library(monkeypatch, has_reader):
    """The declaration is made at import from the library: the plugin's source executed again under another module name
    (registration neutralised: the registered class is never replaced), once with a library that has
    ``ottieni_profilo_societa`` and once without, whichever library is installed."""
    original = importlib.import_module(PLUGIN_MODULE).BorsaItalianaEnricher
    registered: list[type] = []
    with monkeypatch.context() as patch:
        if has_reader:
            patch.setattr(bis, "ottieni_profilo_societa", lambda *a, **k: pytest.fail("the probe module made a call"), raising=False)
        else:
            patch.delattr(bis, "ottieni_profilo_societa", raising=False)
        patch.setattr(EnricherRegistry, "register", staticmethod(registered.append), raising=True)
        spec = importlib.util.spec_from_file_location("borsa_italiana_plugin_probe", importlib.util.find_spec(PLUGIN_MODULE).origin)
        probe = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(probe)

    assert registered == [probe.BorsaItalianaEnricher], f"barrier: the module body ran and handed its class once: {registered}"
    assert (probe.ottieni_profilo_societa is not None) is has_reader
    voices = probe.BorsaItalianaEnricher.voices
    assert voices[AssetType.STOCK] == (STOCK_VOICES | PROFILE_VOICES if has_reader else STOCK_VOICES), sorted(voices[AssetType.STOCK])
    assert len(voices[AssetType.STOCK]) == (7 if has_reader else 2), sorted(voices[AssetType.STOCK])
    assert voices[AssetType.BOND] == BOND_VOICES and voices[AssetType.FUND] == FUND_VOICES, "the other types do not depend on it"
    assert hasattr(bis, "ottieni_profilo_societa") is LIBRARY_HAS_PROFILE, "barrier: the installed library is back as it was"
    monkeypatch.setenv(TEST_MODE_VARIABLE, "1")
    assert EnricherRegistry.get_plugin(CODE) is original, "the registered class is still the original"


# --- BI-PROF: the two figures of the last fiscal year -------------------------------------------------------------------

#: The labels of the «main data» rows the figures read, per page language.
_LABELS = {
    "en": {"revenue": "Net sales", "net_income": "Net income", "group": "Net income (Group share)", "end": "Fiscal year end", "unit": "Currency & Unit"},
    "it": {"revenue": "Fatturato", "net_income": "Utile netto", "group": "Utile netto: quota del gruppo", "end": "Chiusura esercizio fiscale", "unit": "Valuta e unità di misura"},
}
_END_2025, _END_2024 = date(2025, 12, 31), date(2024, 12, 31)


def _main_data(language: str = "en", *, revenue=None, net_income=None, group=None, units=None, ends=None, first: tuple[str, ...] = ()) -> list[Any]:
    """A synthetic «main data» table: each argument the values by year of its row (None: no row). ``first`` lists the
    rows written before the others, by name."""
    labels = _LABELS[language]
    given = {"revenue": revenue, "net_income": net_income, "group": group, "end": ends, "unit": units}
    order = [*first, *(name for name in given if name not in first)]
    return [_datum(labels[name], given[name]) for name in order if given[name] is not None]


def _figures(plugin, library: FakeLibrary, rows: list[Any], language: str = "en") -> tuple[dict[str, Any], dict[str, date], list[dict[str, Any]]]:
    """Enel's profile with ``rows`` as its «main data»: the stored figures, their dates and the log lines of the read."""
    with capture_logs() as events:
        item = _read_one(plugin, _enel(library, language, _profile(language, dati_principali=rows)))
    assert item.status == EnricherReadStatus.OK, item
    assert {"description", "issuer_country", "website"} <= set(item.values), "barrier: the page's other voices are read"
    stored = _stored(item.values)
    figures = {key: stored[key] for key in FISCAL_VOICES if key in stored}
    dates = {key: day for key, day in dict(item.source_dates).items() if key in FISCAL_VOICES}
    return figures, dates, events


@pytest.mark.parametrize(
    ("language", "unit", "revenue", "net_income"),
    [
        ("en", "EUR - units", "78057", "5617"),
        ("en", "EUR - thousands", "78057000", "5617000"),
        ("en", "EUR - millions", "78057000000", "5617000000"),
        ("en", "EUR - billions", "78057000000000", "5617000000000"),
        ("it", "EUR - unità", "78057", "5617"),
        ("it", "EUR - migliaia", "78057000", "5617000"),
        ("it", "EUR - milioni", "78057000000", "5617000000"),
        ("it", "EUR - miliardi", "78057000000000", "5617000000000"),
        ("en", "EUR - Millions", "78057000000", "5617000000"),
        ("it", "eur - MILIONI", "78057000000", "5617000000"),
        ("en", "USD - thousands", "78057000", "5617000"),
    ],
)
def test_figures_are_scaled_by_the_unit_of_their_year(plugin, library, language, unit, revenue, net_income):
    """«78057» in «EUR - millions» is 78 057 000 000 EUR: the unit's word (either language, any case) is the factor, the
    part before « - » the currency (upper case); both figures dated by the fiscal year end of their year."""
    currency = unit.split(" - ")[0].upper()
    rows = _main_data(language, revenue={2025: Decimal("78057")}, net_income={2025: Decimal("5617")}, units={2025: unit}, ends={2025: _END_2025})
    figures, dates, _events = _figures(plugin, library, rows, language)
    assert figures == {"revenue": {"amount": revenue, "currency": currency}, "net_income": {"amount": net_income, "currency": currency}}
    assert dates == dict.fromkeys(FISCAL_VOICES, _END_2025)


def test_a_fraction_in_billions_and_a_loss(plugin, library):
    """A figure with decimals is scaled exactly (1.5 billions is 1 500 000 000); a negative net income (a loss) passes
    the catalogue, whose net income may be negative."""
    rows = _main_data(revenue={2025: Decimal("1.5")}, net_income={2025: Decimal("-0.371")}, units={2025: "EUR - billions"}, ends={2025: _END_2025})
    figures, _dates, _events = _figures(plugin, library, rows)
    assert figures == {"revenue": {"amount": "1500000000", "currency": "EUR"}, "net_income": {"amount": "-371000000", "currency": "EUR"}}


def test_an_empty_cell_falls_back_to_the_year_before(plugin, library):
    """2025's revenue cell is empty: the revenue is 2024's, in 2024's unit and dated by 2024's end; the net income, given
    for 2025, stays 2025's. Each figure finds its own year."""
    rows = _main_data(
        revenue={2025: None, 2024: Decimal("73914"), 2023: Decimal("92882")},
        net_income={2025: Decimal("5617"), 2024: Decimal("8229")},
        units={2025: "EUR - millions", 2024: "EUR - thousands"},
        ends={2025: _END_2025, 2024: _END_2024},
    )
    figures, dates, _events = _figures(plugin, library, rows)
    assert figures == {"revenue": {"amount": "73914000", "currency": "EUR"}, "net_income": {"amount": "5617000000", "currency": "EUR"}}
    assert dates == {"revenue": _END_2024, "net_income": _END_2025}


def test_a_text_cell_is_not_a_figure(plugin, library):
    """A cell that is not a number (a «n.d.» text) is skipped like an empty one."""
    rows = _main_data(revenue={2025: "n.d.", 2024: Decimal("73914")}, units={2025: "EUR - millions", 2024: "EUR - millions"}, ends={2025: _END_2025, 2024: _END_2024})
    figures, dates, _events = _figures(plugin, library, rows)
    assert figures == {"revenue": {"amount": "73914000000", "currency": "EUR"}}
    assert dates == {"revenue": _END_2024}


@pytest.mark.parametrize("unit", ["EUR - trillions", "EUR", "EUR millions", "euro - millions", "EUR - "], ids=["unknown-word", "no-scale", "no-dash", "not-a-code", "empty-scale"])
def test_an_unknown_unit_leaves_both_figures_out_with_one_log_line(plugin, library, unit):
    """A unit the plugin cannot translate: neither figure (never a guessed scale), one warning naming the unit (as the
    page writes it, trimmed) for the profile, not one per figure."""
    rows = _main_data(revenue={2025: Decimal("78057")}, net_income={2025: Decimal("5617")}, units={2025: unit}, ends={2025: _END_2025})
    figures, dates, events = _figures(plugin, library, rows)
    assert figures == {} and dates == {}
    assert len([event for event in _warnings_naming(events, ENEL_ISIN) if unit.strip() in repr(event)]) == 1, f"one warning names the unit {unit!r}: {events}"


def test_an_unknown_unit_with_one_figure_logs_one_line(plugin, library):
    """Only the revenue row and an unknown unit: no figure, one warning (the case the per-profile rule above shares)."""
    rows = _main_data(revenue={2025: Decimal("78057")}, units={2025: "EUR - trillions"}, ends={2025: _END_2025})
    figures, dates, events = _figures(plugin, library, rows)
    assert figures == {} and dates == {}
    assert len([event for event in _warnings_naming(events, ENEL_ISIN) if "EUR - trillions" in repr(event)]) == 1, events


@pytest.mark.parametrize(
    ("units", "ends"),
    [(None, {2025: _END_2025}), ({2024: "EUR - millions"}, {2025: _END_2025, 2024: _END_2024}), ({2025: "EUR - millions"}, None), ({2025: "EUR - millions"}, {2024: _END_2024}), ({2025: "EUR - millions"}, {2025: "31/12/2025"})],
    ids=["no-unit-row", "no-unit-for-the-year", "no-end-row", "no-end-for-the-year", "end-not-a-date"],
)
def test_a_year_without_its_unit_or_its_end_gives_no_figure_silently(plugin, library, units, ends):
    """The year of the figure has no unit or no fiscal year end (a date): no figure and no log line; never the unit or
    the date of another year."""
    rows = _main_data(revenue={2025: Decimal("78057")}, net_income={2025: Decimal("5617")}, units=units, ends=ends)
    figures, dates, events = _figures(plugin, library, rows)
    assert figures == {} and dates == {}
    assert _warnings_naming(events, ENEL_ISIN) == [], events


@pytest.mark.parametrize("language", LANGUAGES)
def test_the_group_share_row_is_never_the_net_income(plugin, library, language):
    """Only «Net income (Group share)» / «Utile netto: quota del gruppo» on the page: no net income (the group's share
    is another figure); written before the plain row, the plain row still wins."""
    alone = _main_data(language, revenue={2025: Decimal("78057")}, group={2025: Decimal("4261")}, units={2025: "EUR - millions"}, ends={2025: _END_2025})
    figures, _dates, _events = _figures(plugin, library, alone, language)
    assert figures == {"revenue": {"amount": "78057000000", "currency": "EUR"}}

    library.profiles.clear()
    first = _main_data(language, net_income={2025: Decimal("5617")}, group={2025: Decimal("4261")}, units={2025: "EUR - millions"}, ends={2025: _END_2025}, first=("group",))
    assert first[0].voce == _LABELS[language]["group"], "barrier: the group's share is the first row"
    figures, _dates, _events = _figures(plugin, library, first, language)
    assert figures == {"net_income": {"amount": "5617000000", "currency": "EUR"}}


def test_row_labels_in_any_case(plugin, library):
    """The row labels are matched without regard to case («NET SALES», «fiscal YEAR end»)."""
    rows = [
        _datum("NET SALES", {2025: Decimal("78057")}),
        _datum("net income", {2025: Decimal("5617")}),
        _datum("FISCAL year END", {2025: _END_2025}),
        _datum("currency & UNIT", {2025: "EUR - millions"}),
    ]
    figures, dates, _events = _figures(plugin, library, rows)
    assert figures == ENEL_FIGURES and dates == dict.fromkeys(FISCAL_VOICES, _END_2025)


# --- BI-PROF: the website -------------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("given", "stored"),
    [
        ("https://www.enel.com/investors/overview", "https://www.enel.com/investors/overview"),
        ("http://www.enel.it", "http://www.enel.it"),
        ("HTTPS://WWW.ENEL.COM", "HTTPS://WWW.ENEL.COM"),
        ("www.enel.com", "https://www.enel.com"),
        ("enel.com/investors", "https://enel.com/investors"),
        ("  www.enel.com  ", "https://www.enel.com"),
    ],
    ids=["https", "http", "upper-case-scheme", "bare-www", "bare-with-path", "padded"],
)
def test_website_is_a_web_address(plugin, library, given, stored):
    """``contatti.sito_web``: kept when it starts with http(s)://, «https://» put before a bare domain; dated by the
    page's last update; no log line."""
    with capture_logs() as events:
        item = _read_one(plugin, _enel(library, profile=_with_website(_profile(), given)))
    assert item.status == EnricherReadStatus.OK, item
    assert _stored(item.values)["website"] == stored
    assert item.source_dates["website"] == PROFILE_DATE
    assert _warnings_naming(events, ENEL_ISIN) == [], events


@pytest.mark.parametrize("given", ["mailto:investor.relations@enel.com", "investor.relations@enel.com", "ftp://ftp.enel.com", "javascript:alert(1)", "enel", "www.enel .com"], ids=["mailto", "e-mail", "ftp", "javascript", "word", "inner-space"])
def test_website_not_a_web_address_is_absent_with_one_log_line(plugin, library, given):
    """Anything that is not a web address: no ``website`` (never a link the tab could open), one warning naming it; the
    other voices stay."""
    with capture_logs() as events:
        item = _read_one(plugin, _enel(library, profile=_with_website(_profile(), given)))
    assert item.status == EnricherReadStatus.OK, item
    assert "website" not in item.values and "website" not in item.source_dates, item.values
    assert {"description", "issuer_country", *FISCAL_VOICES} <= set(item.values), item.values
    assert len([event for event in _warnings_naming(events, ENEL_ISIN) if given in repr(event)]) == 1, f"one warning names {given!r}: {events}"


@pytest.mark.parametrize("given", [None, "", "   "], ids=["none", "empty", "blank"])
def test_no_website_is_absent_and_silent(plugin, library, given):
    with capture_logs() as events:
        item = _read_one(plugin, _enel(library, profile=_with_website(_profile(), given)))
    assert item.status == EnricherReadStatus.OK, item
    assert "website" not in item.values and PAGE_VOICES - {"website"} <= set(item.values), item.values
    assert _warnings_naming(events, ENEL_ISIN) == [], events
