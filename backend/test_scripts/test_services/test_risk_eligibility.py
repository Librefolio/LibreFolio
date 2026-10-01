"""Whether an asset's own quotes can take part in a risk analysis or a historical replay.

Developer's decision of 24/09/2026. One set of facts per asset and window, read two ways:

- analysis eligibility (a period chosen by the user): no quote, no FX route or fewer quotes than
  the analytics accept make an asset ineligible; starting late or going stale before the end is a
  warning;
- replay coverage (a crisis window): the asset must be priced at both ends, within the staleness
  threshold, or the replay excludes it on its own — before the joint series is prepared, so that a
  late starter cannot move the joint baseline and shorten the replay of every other asset.

The rules are pure and tested at their boundaries; the loader and the service path run against
rows this module writes to the test database and deletes afterwards.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

from backend.app.db.models import Asset, AssetType, FxRate, PriceHistory  # noqa: E402
from backend.app.db.session import get_async_engine  # noqa: E402
from backend.app.schemas.common import DateRangeModel  # noqa: E402
from backend.app.schemas.portfolio import DataQualityStatus  # noqa: E402
from backend.app.schemas.risk import (  # noqa: E402
    RiskEligibilityLevel,
    RiskEligibilityReason,
    RiskEligibilityRequest,
    RiskEligibilityResponse,
    RiskErrorCode,
    RiskHistoricalReplayExclusionReason,
    RiskHistoricalReplayExclusionTreatment,
    RiskQueryRequest,
    RiskResultStatus,
)
from backend.app.services.data_quality_thresholds import RISK_MIN_OBSERVATIONS, STALE_PRICE_THRESHOLD_DAYS  # noqa: E402
from backend.app.services.risk import service as risk_service_module  # noqa: E402
from backend.app.services.risk.eligibility import (  # noqa: E402
    PriceWindowFacts,
    analysis_eligibility,
    common_quoted_range,
    load_price_window_facts,
    period_limits_coverage,
    replay_coverage,
    suggested_analysis_ranges,
    suggested_replay_range,
)
from backend.app.services.risk.service import RiskService  # noqa: E402

Level = RiskEligibilityLevel
Why = RiskEligibilityReason
Excluded = RiskHistoricalReplayExclusionReason

START = date(2025, 3, 3)
END = date(2025, 6, 30)
STALE = STALE_PRICE_THRESHOLD_DAYS
FLOOR = RISK_MIN_OBSERVATIONS


def days(count: int) -> timedelta:
    return timedelta(days=count)


SAME_AS_WINDOW = object()


def facts(
    *,
    first: date | None = START,
    last: date | None = END,
    before: date | None = None,
    quotes: int = FLOOR,
    fx: bool = True,
    first_in: date | None = None,
    first_ever: object = SAME_AS_WINDOW,
    last_ever: object = SAME_AS_WINDOW,
) -> PriceWindowFacts:
    """Facts of an asset quoted from the start to the end of the window, unless told otherwise.

    The whole history defaults to the one seen up to the window end, as the loader would read it
    for an asset with no quote after the window.
    """
    return PriceWindowFacts(
        first_quote=first,
        last_quote=last,
        last_quote_before_start=before,
        quotes_in_window=quotes,
        fx_available=fx,
        first_quote_in_window=first_in,
        first_quote_ever=first if first_ever is SAME_AS_WINDOW else first_ever,
        last_quote_ever=last if last_ever is SAME_AS_WINDOW else last_ever,
    )


# ---------------------------------------------------------------------------
# Analysis eligibility: the boundaries of each rule
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("window_facts", "expected"),
    [
        # Never quoted is told apart from not quoted in the period: only the second a period can mend.
        pytest.param(facts(first=None, last=None, quotes=0), (Level.INELIGIBLE, (Why.NO_PRICE_HISTORY,)), id="never-quoted"),
        pytest.param(facts(first=None, last=None, quotes=0, fx=False), (Level.INELIGIBLE, (Why.NO_PRICE_HISTORY, Why.MISSING_FX)), id="never-quoted-with-missing-fx"),
        pytest.param(facts(first=START - days(90), last=START - days(30), before=START - days(30), quotes=0), (Level.INELIGIBLE, (Why.NO_PRICES,)), id="quoted-only-before-the-period"),
        pytest.param(
            facts(first=START - days(90), last=START - days(30), before=START - days(30), quotes=0, fx=False),
            (Level.INELIGIBLE, (Why.NO_PRICES, Why.MISSING_FX)),
            id="quoted-only-before-with-missing-fx",
        ),
        pytest.param(facts(first=None, last=None, quotes=0, first_ever=END + days(10), last_ever=END + days(40)), (Level.INELIGIBLE, (Why.NO_PRICES,)), id="quoted-only-after-the-period"),
        pytest.param(facts(quotes=FLOOR - 1), (Level.INELIGIBLE, (Why.TOO_FEW_QUOTES,)), id="one-quote-short-of-the-floor"),
        pytest.param(facts(quotes=FLOOR), (Level.ELIGIBLE, ()), id="exactly-the-floor"),
        pytest.param(facts(fx=False), (Level.INELIGIBLE, (Why.MISSING_FX,)), id="missing-fx-alone"),
        pytest.param(facts(quotes=FLOOR - 1, fx=False), (Level.INELIGIBLE, (Why.TOO_FEW_QUOTES, Why.MISSING_FX)), id="missing-fx-with-too-few-quotes"),
        pytest.param(facts(first=START + days(STALE)), (Level.ELIGIBLE, ()), id="first-quote-at-the-threshold-after-start"),
        pytest.param(facts(first=START + days(STALE + 1)), (Level.WARNING, (Why.STARTS_LATE,)), id="first-quote-one-day-later"),
        pytest.param(facts(last=END - days(STALE)), (Level.ELIGIBLE, ()), id="last-quote-at-the-threshold-before-end"),
        pytest.param(facts(last=END - days(STALE + 1)), (Level.WARNING, (Why.STALE_AT_END,)), id="last-quote-one-day-earlier"),
        pytest.param(facts(first=START + days(STALE + 1), last=END - days(STALE + 1)), (Level.WARNING, (Why.STARTS_LATE, Why.STALE_AT_END)), id="both-warnings"),
        pytest.param(facts(first=START - days(400), before=START - days(1)), (Level.ELIGIBLE, ()), id="history-older-than-the-period-is-not-late"),
        pytest.param(facts(first=START + days(STALE + 1), quotes=FLOOR - 1), (Level.INELIGIBLE, (Why.TOO_FEW_QUOTES,)), id="a-blocking-reason-leaves-no-warning"),
    ],
)
def test_analysis_eligibility_at_the_boundaries_of_each_rule(window_facts, expected):
    assert analysis_eligibility(window_facts, START, END) == expected


# Whether the chosen period, not the asset's own history, leaves the asset short (developer's
# decision of 24/09/2026): read from the facts, because a blocking reason hides the warnings.


@pytest.mark.parametrize(
    ("window_facts", "limited", "reported"),
    [
        pytest.param(facts(first=None, last=None, quotes=0), False, (Why.NO_PRICE_HISTORY,), id="never-quoted"),
        pytest.param(facts(first=START - days(90), last=START - days(30), before=START - days(30), quotes=0), True, (Why.NO_PRICES,), id="quoted-only-before"),
        pytest.param(facts(first=None, last=None, quotes=0, first_ever=END + days(10), last_ever=END + days(40)), True, (Why.NO_PRICES,), id="quoted-only-after"),
        pytest.param(facts(first=START + days(STALE)), False, (), id="first-quote-at-the-threshold"),
        pytest.param(facts(first=START + days(STALE + 1)), True, (Why.STARTS_LATE,), id="first-quote-one-day-later"),
        pytest.param(facts(last=END - days(STALE)), False, (), id="last-quote-at-the-threshold"),
        pytest.param(facts(last=END - days(STALE + 1)), True, (Why.STALE_AT_END,), id="last-quote-one-day-earlier"),
        # A blocking reason reports no warning, yet the late start is still there to mend.
        pytest.param(facts(first=START + days(STALE + 1), quotes=FLOOR - 1), True, (Why.TOO_FEW_QUOTES,), id="too-few-quotes-hiding-a-late-start"),
        pytest.param(facts(last=END - days(STALE + 1), quotes=FLOOR - 1), True, (Why.TOO_FEW_QUOTES,), id="too-few-quotes-hiding-a-stale-end"),
        pytest.param(facts(first=START + days(STALE + 1), fx=False), True, (Why.MISSING_FX,), id="missing-fx-hiding-a-late-start"),
        # Too few quotes over the whole period, fresh at both ends: no period mends that.
        pytest.param(facts(first=START - days(400), before=START - days(3), last=END - days(2), quotes=FLOOR - 5), False, (Why.TOO_FEW_QUOTES,), id="sparse-throughout-not-late-fresh-at-the-end"),
    ],
)
def test_period_limits_coverage_reads_the_facts_not_the_reasons(window_facts, limited, reported):
    assert period_limits_coverage(window_facts, START, END) is limited
    assert analysis_eligibility(window_facts, START, END)[1] == reported


# ---------------------------------------------------------------------------
# Replay coverage: priced at both ends of the crisis window
# ---------------------------------------------------------------------------

# Developer's decision of 24/09/2026: the exclusion rule is unchanged, but its reason is split so the
# sentence shown is never false. At the start, an asset quoted before the window with no recent quote
# (a gap, a sparse rhythm such as a monthly NAV) is stale — only a new listing gets the tolerance
# after the start. At the end the facts stop at the window end, so a gap and a delisting read alike.
DAILY_AFTER_START = (END - START).days


@pytest.mark.parametrize(
    ("window_facts", "expected"),
    [
        # Start, an asset quoted before the window.
        pytest.param(facts(first=START - days(30), before=START - days(STALE)), None, id="gap-ending-at-the-threshold-before-start-is-covered"),
        pytest.param(facts(first=START - days(400), before=START - days(STALE), quotes=4), None, id="monthly-rhythm-quoted-at-the-threshold-before-start-is-covered"),
        pytest.param(facts(first=START - days(30), before=START - days(STALE + 1)), Excluded.STALE_AT_WINDOW_START, id="gap-one-day-too-old-is-stale-at-start"),
        pytest.param(
            facts(first=START - days(30), before=START - days(STALE + 1), quotes=DAILY_AFTER_START),
            Excluded.STALE_AT_WINDOW_START,
            id="gap-quoted-daily-right-after-the-start-is-still-stale",
        ),
        pytest.param(facts(first=START - days(400), before=START - days(20), quotes=4), Excluded.STALE_AT_WINDOW_START, id="monthly-nav-is-stale-at-start-not-a-late-starter"),
        # Start, a listing inside the window.
        pytest.param(facts(first=START), None, id="listed-on-the-first-day"),
        pytest.param(facts(first=START + days(STALE)), None, id="listed-at-the-threshold-after-start-is-covered"),
        pytest.param(facts(first=START + days(STALE + 1)), Excluded.STARTS_AFTER_WINDOW_START, id="listed-one-day-later-starts-after-the-window"),
        # End: one neutral reason.
        pytest.param(facts(last=END - days(STALE)), None, id="end-covered-at-the-threshold"),
        pytest.param(facts(last=END - days(STALE + 1)), Excluded.STALE_AT_WINDOW_END, id="end-one-day-too-old-is-stale-at-end"),
        pytest.param(
            facts(first=START - days(90), last=START - days(STALE), before=START - days(STALE), quotes=0),
            Excluded.STALE_AT_WINDOW_END,
            id="a-quote-just-before-the-window-is-near-it-but-stale-at-end",
        ),
        # Nothing in or near the window.
        pytest.param(facts(first=None, last=None, quotes=0), Excluded.NO_PRICES_IN_WINDOW, id="no-quote-at-all"),
        pytest.param(
            facts(first=START - days(90), last=START - days(STALE + 1), before=START - days(STALE + 1), quotes=0),
            Excluded.NO_PRICES_IN_WINDOW,
            id="quotes-only-well-before-the-window",
        ),
        # A missing rate wins over everything else.
        pytest.param(facts(fx=False), Excluded.MISSING_FX, id="missing-fx-on-a-covered-asset"),
        pytest.param(facts(first=None, last=None, quotes=0, fx=False), Excluded.MISSING_FX, id="missing-fx-wins-over-no-prices"),
        pytest.param(facts(first=START + days(STALE + 1), fx=False), Excluded.MISSING_FX, id="missing-fx-wins-over-a-late-start"),
        pytest.param(facts(first=START - days(30), before=START - days(STALE + 1), fx=False), Excluded.MISSING_FX, id="missing-fx-wins-over-a-gap"),
    ],
)
def test_replay_coverage_at_the_boundaries_of_each_rule(window_facts, expected):
    assert replay_coverage(window_facts, START, END) == expected


# ---------------------------------------------------------------------------
# Common periods: proposals that bring back what the chosen window excludes
# (developer's decisions of 24/09/2026). Pure and unverified here; the service
# verifies each one on a second reading of the facts.
# ---------------------------------------------------------------------------


def history(first: date | None, last: date | None) -> PriceWindowFacts:
    """An asset's whole history, the only facts a common span reads."""
    return PriceWindowFacts(first_quote=None, last_quote=None, last_quote_before_start=None, quotes_in_window=0, first_quote_ever=first, last_quote_ever=last)


@pytest.mark.parametrize(
    ("histories", "expected"),
    [
        pytest.param([history(START, END + days(100)), history(START + days(10), END + days(90)), history(START - days(5), END + days(120))], (START + days(10), END + days(90)), id="latest-first-to-earliest-last"),
        pytest.param([history(START, END), history(None, None)], (START, END), id="an-asset-never-quoted-is-left-out"),
        pytest.param([history(START, START + days(10)), history(START + days(20), START + days(30))], None, id="disjoint-spans"),
        pytest.param([history(START, START + days(10)), history(START + days(10), START + days(20))], None, id="spans-touching-on-one-day"),
        pytest.param([history(None, None)], None, id="nothing-quoted"),
        pytest.param([], None, id="no-asset"),
    ],
)
def test_common_quoted_range(histories, expected):
    assert common_quoted_range(histories) == expected


@pytest.mark.parametrize(
    ("common", "expected"),
    [
        # The span starts the day after the latest first quote, so that quote is the starting price.
        pytest.param((START + days(10), END + days(50)), ((START + days(11), END), (START + days(11), END + days(50))), id="trim-the-start-then-fall-back-to-the-span"),
        pytest.param((START, END + days(50)), ((START + days(1), END), (START + days(1), END + days(50))), id="a-first-quote-on-the-start-day-still-starts-the-day-after"),
        pytest.param((START - days(50), END - days(10)), ((START, END - days(10)), (START - days(49), END - days(10))), id="trim-the-end-then-fall-back-to-the-span"),
        pytest.param((START + days(10), END - days(10)), ((START + days(11), END - days(10)),), id="trimmed-at-both-ends-is-the-span"),
        pytest.param((END + days(10), END + days(100)), ((END + days(11), END + days(100)),), id="disjoint-after-shifts-to-the-span"),
        pytest.param((START - days(100), START - days(10)), ((START - days(99), START - days(10)),), id="disjoint-before-shifts-to-the-span"),
        pytest.param((END - days(1), END + days(30)), ((END, END + days(30)),), id="a-one-day-overlap-is-empty-and-shifts"),
        # The period already lies inside the span: its trouble is a gap no span mends.
        pytest.param((START - days(50), END + days(50)), (), id="period-inside-the-span"),
        pytest.param((START - days(1), END + days(50)), (), id="period-starting-the-day-after-the-common-start"),
        pytest.param((START, START + days(1)), (), id="a-span-of-one-day-after-the-first-quote-is-empty"),
        pytest.param(None, (), id="no-common-span"),
    ],
)
def test_suggested_analysis_ranges(common, expected):
    assert suggested_analysis_ranges(common, START, END) == expected


LISTED = START + days(10)


@pytest.mark.parametrize(
    ("window_facts", "auto", "expected"),
    [
        # A late start begins the day after the first quote inside the window.
        pytest.param({1: facts(first=LISTED, first_in=LISTED)}, {1: Excluded.STARTS_AFTER_WINDOW_START}, ((LISTED + days(1), END), (1,)), id="late-listing"),
        pytest.param(
            {1: facts(first=START - days(30), before=START - days(STALE + 3), first_in=START + days(2))},
            {1: Excluded.STALE_AT_WINDOW_START},
            ((START + days(3), END), (1,)),
            id="gap-at-the-start-recovers",
        ),
        pytest.param({1: facts(last=END - days(10))}, {1: Excluded.STALE_AT_WINDOW_END}, ((START, END - days(10)), (1,)), id="stale-end"),
        pytest.param({1: facts(first=LISTED, first_in=LISTED, last=END - days(10))}, {1: Excluded.STARTS_AFTER_WINDOW_START}, ((LISTED + days(1), END - days(10)), (1,)), id="both-edges-on-one-asset"),
        pytest.param({1: facts(first=LISTED, first_in=LISTED, last=END - days(STALE))}, {1: Excluded.STARTS_AFTER_WINDOW_START}, ((LISTED + days(1), END), (1,)), id="a-recent-last-quote-keeps-the-end"),
        pytest.param(
            {
                4: facts(first=LISTED, first_in=LISTED),
                2: facts(first=START - days(30), before=START - days(20), first_in=START + days(20)),
                3: facts(last=END - days(10)),
                1: facts(last=END - days(20)),
            },
            {4: Excluded.STARTS_AFTER_WINDOW_START, 2: Excluded.STALE_AT_WINDOW_START, 3: Excluded.STALE_AT_WINDOW_END, 1: Excluded.STALE_AT_WINDOW_END},
            ((START + days(21), END - days(20)), (1, 2, 3, 4)),
            id="latest-start-earliest-end-and-sorted-recovers",
        ),
        pytest.param(
            {1: facts(first=LISTED, first_in=LISTED), 2: facts(first=None, last=None, quotes=0), 3: facts(fx=False)},
            {1: Excluded.STARTS_AFTER_WINDOW_START, 2: Excluded.NO_PRICES_IN_WINDOW, 3: Excluded.MISSING_FX},
            ((LISTED + days(1), END), (1,)),
            id="no-prices-and-missing-fx-are-not-recovered",
        ),
        pytest.param(
            {2: facts(first=None, last=None, quotes=0), 3: facts(fx=False)},
            {2: Excluded.NO_PRICES_IN_WINDOW, 3: Excluded.MISSING_FX},
            None,
            id="only-no-prices-and-missing-fx",
        ),
        pytest.param({}, {}, None, id="nothing-excluded"),
        pytest.param({1: facts(first=END - days(2), first_in=END - days(2))}, {1: Excluded.STARTS_AFTER_WINDOW_START}, ((END - days(1), END), (1,)), id="the-day-after-still-before-the-end"),
        pytest.param({1: facts(first=END - days(1), first_in=END - days(1))}, {1: Excluded.STARTS_AFTER_WINDOW_START}, None, id="the-day-after-reaching-the-end"),
        pytest.param(
            {1: facts(first=START + days(50), first_in=START + days(50)), 2: facts(last=START + days(40))},
            {1: Excluded.STARTS_AFTER_WINDOW_START, 2: Excluded.STALE_AT_WINDOW_END},
            None,
            id="a-start-after-another-assets-end",
        ),
        pytest.param({1: facts(first=LISTED, first_in=None)}, {1: Excluded.STARTS_AFTER_WINDOW_START}, None, id="late-start-without-a-first-quote-in-the-window"),
        pytest.param({1: facts(last=None)}, {1: Excluded.STALE_AT_WINDOW_END}, None, id="edge-asset-without-a-last-quote"),
    ],
)
def test_suggested_replay_range(window_facts, auto, expected):
    assert suggested_replay_range(window_facts, auto, START, END) == expected


@pytest.mark.asyncio
async def test_price_window_facts_of_no_asset_touch_no_database():
    class Untouchable:
        async def execute(self, *_args, **_kwargs):
            raise AssertionError("no query expected for an empty asset list")

    assert await load_price_window_facts(Untouchable(), asset_ids=[], window_start=START, window_end=END, target_currency="EUR") == {}


# ---------------------------------------------------------------------------
# Against the test database
# ---------------------------------------------------------------------------

# A quarter for the loader (T8) and an eight-week crisis, Monday to Friday, for the replay (T7).
LOADER_START = date(2012, 4, 2)
LOADER_END = date(2012, 6, 29)
CRISIS_START = date(2011, 3, 7)
CRISIS_END = date(2011, 4, 29)
# Two market holidays of one asset, one of them on a Monday: carried one and three days.
HOLIDAYS = frozenset({CRISIS_START + days(10), CRISIS_START + days(21)})
LATE_FIRST_QUOTE = CRISIS_START + days(15)
# An old history with a gap across the crisis start: last quote ten days before it, then quoting again
# two days in — the kind of asset a first quote read inside the window would mistake for a listing.
GAP_FIRST_QUOTE = CRISIS_START - days(60)
GAP_LAST_QUOTE_BEFORE = CRISIS_START - days(10)
GAP_RESUMES = CRISIS_START + days(2)
PRICE_ORIGIN = date(2011, 1, 1)
# Currencies nothing else in the suite stores a rate for.
NO_RATE_CURRENCY = "KES"
PROBED_CURRENCY = "EGP"
ANALYSIS_FX_CURRENCY = "NGN"

# Analysis proposals (C1): a quarter of 2014 inside a history running from December to December.
ANALYSIS_START = date(2014, 3, 3)
ANALYSIS_END = date(2014, 6, 30)
HISTORY_FIRST = date(2013, 12, 1)
HISTORY_LAST = date(2014, 12, 31)
ANALYSIS_LATE_FIRST = date(2014, 4, 1)
ANALYSIS_ENDS = date(2014, 6, 10)
ANALYSIS_AFTER_FIRST = date(2014, 8, 1)
# A second period, for a candidate that misses an FX rate at its start.
FX_PERIOD_START = date(2014, 9, 1)
FX_PERIOD_END = date(2014, 11, 30)


def every_day(first: date, last: date) -> list[date]:
    return [first + days(offset) for offset in range((last - first).days + 1)]


def every_week(first: date, last: date) -> list[date]:
    return [first + days(offset) for offset in range(0, (last - first).days + 1, 7)]


def weekdays(first: date, last: date, *, skip: frozenset[date] = frozenset()) -> list[date]:
    return [day for day in every_day(first, last) if day.weekday() < 5 and day not in skip]


ASSETS: dict[str, tuple[str, Decimal, list[date]]] = {
    # Loader: quotes around the window, one past its end; one asset quoted only after it.
    "full": ("EUR", Decimal("1"), [LOADER_START - days(10), LOADER_START - days(3), *every_day(LOADER_START, LOADER_END - days(2)), LOADER_END + days(5)]),
    "empty": ("EUR", Decimal("1"), []),
    "no_rate": (NO_RATE_CURRENCY, Decimal("1"), every_day(LOADER_START, LOADER_END)),
    "probed": (PROBED_CURRENCY, Decimal("1"), every_day(LOADER_START, LOADER_END)),
    "after_only": ("EUR", Decimal("1"), every_day(LOADER_END + days(10), LOADER_END + days(20))),
    # Replay: two assets quoted through the crisis, one that starts in the middle of it, one
    # quoted long before it whose quotes pause across its start, and a sparse one priced at both
    # ends of the crisis but three weeks apart inside it.
    "early": ("EUR", Decimal("0.5"), weekdays(CRISIS_START - days(14), CRISIS_END)),
    "holiday": ("EUR", Decimal("0.25"), weekdays(CRISIS_START - days(14), CRISIS_END, skip=HOLIDAYS)),
    "late": ("EUR", Decimal("1"), weekdays(LATE_FIRST_QUOTE, CRISIS_END)),
    "gapped": ("EUR", Decimal("0.75"), [*weekdays(GAP_FIRST_QUOTE, GAP_LAST_QUOTE_BEFORE), *weekdays(GAP_RESUMES, CRISIS_END)]),
    "sparse": ("EUR", Decimal("1"), [CRISIS_START - days(3), date(2011, 3, 25), date(2011, 4, 15), date(2011, 4, 25)]),
    # Analysis proposals: one shape per eligibility reason.
    "a_full": ("EUR", Decimal("1"), every_day(HISTORY_FIRST, HISTORY_LAST)),
    "a_late": ("EUR", Decimal("1"), every_day(ANALYSIS_LATE_FIRST, HISTORY_LAST)),
    "a_ends": ("EUR", Decimal("1"), every_day(HISTORY_FIRST, ANALYSIS_ENDS)),
    "a_after": ("EUR", Decimal("1"), every_day(ANALYSIS_AFTER_FIRST, HISTORY_LAST)),
    "a_starts3": ("EUR", Decimal("1"), every_day(ANALYSIS_START + days(3), HISTORY_LAST)),
    "a_weekly": ("EUR", Decimal("1"), every_week(HISTORY_FIRST, HISTORY_LAST)),
    "a_kes": (NO_RATE_CURRENCY, Decimal("1"), every_day(HISTORY_FIRST, HISTORY_LAST)),
    "a_never": ("EUR", Decimal("1"), []),
    "a_gap_end": ("EUR", Decimal("1"), [*every_day(HISTORY_FIRST, date(2014, 6, 14)), *every_day(date(2014, 7, 1), HISTORY_LAST)]),
    "a_thin_after": ("EUR", Decimal("1"), [*every_day(HISTORY_FIRST, date(2014, 3, 31)), *every_week(date(2014, 4, 7), date(2014, 12, 29))]),
    "a_late_short": ("EUR", Decimal("1"), every_day(date(2014, 6, 1), date(2014, 7, 10))),
    # Late listings with too few quotes in the period, quoted for months after it.
    "a_late_thin": ("EUR", Decimal("1"), every_day(date(2014, 6, 20), HISTORY_LAST)),
    "a_late_last_day": ("EUR", Decimal("1"), every_day(ANALYSIS_END - days(1), HISTORY_LAST)),
    "a_before": ("EUR", Decimal("1"), every_day(date(2014, 1, 5), date(2014, 6, 30))),
    "a_ngn": (ANALYSIS_FX_CURRENCY, Decimal("1"), every_day(date(2014, 1, 1), HISTORY_LAST)),
}


def close(key: str, day: date) -> Decimal:
    return Decimal("100") + Decimal((day - PRICE_ORIGIN).days) * ASSETS[key][1]


@dataclass(frozen=True)
class WindowAssets:
    ids: dict[str, int]
    names: dict[str, str]


def session() -> AsyncSession:
    return AsyncSession(get_async_engine(), expire_on_commit=False)


@pytest.fixture(scope="module")
def window_assets():
    marker = uuid4().hex

    async def setup() -> WindowAssets:
        async with session() as db:
            assets = {key: Asset(display_name=f"Window {key} {marker}", currency=currency, asset_type=AssetType.STOCK, active=True) for key, (currency, _step, _days) in ASSETS.items()}
            db.add_all(assets.values())
            await db.flush()
            db.add_all(PriceHistory(asset_id=assets[key].id, date=day, close=close(key, day), currency=currency, source_plugin_key="window_test") for key, (currency, _step, quote_days) in ASSETS.items() for day in quote_days)
            await db.commit()
            return WindowAssets(ids={key: asset.id for key, asset in assets.items()}, names={key: asset.display_name for key, asset in assets.items()})

    async def cleanup(data: WindowAssets) -> None:
        async with session() as db:
            owned = list(data.ids.values())
            await db.execute(delete(PriceHistory).where(PriceHistory.asset_id.in_(owned)))
            await db.execute(delete(Asset).where(Asset.id.in_(owned)))
            await db.commit()

    data = asyncio.run(setup())
    yield data
    asyncio.run(cleanup(data))


@pytest.mark.asyncio
async def test_price_window_facts_read_each_assets_own_quotes(window_assets):
    ids = window_assets.ids

    async with session() as db:
        facts_by_asset = await load_price_window_facts(
            db,
            asset_ids=[ids["full"], ids["empty"], ids["after_only"], ids["full"]],
            window_start=LOADER_START,
            window_end=LOADER_END,
            target_currency="EUR",
        )

    assert set(facts_by_asset) == {ids["full"], ids["empty"], ids["after_only"]}
    # The quote past the end is not "the last quote on or before the end", but it is the last ever.
    assert facts_by_asset[ids["full"]] == PriceWindowFacts(
        first_quote=LOADER_START - days(10),
        last_quote=LOADER_END - days(2),
        last_quote_before_start=LOADER_START - days(3),
        quotes_in_window=len(every_day(LOADER_START, LOADER_END - days(2))),
        fx_available=True,
        first_quote_in_window=LOADER_START,
        first_quote_ever=LOADER_START - days(10),
        last_quote_ever=LOADER_END + days(5),
    )
    assert facts_by_asset[ids["empty"]] == PriceWindowFacts(first_quote=None, last_quote=None, last_quote_before_start=None, quotes_in_window=0, fx_available=True)
    # Quoted only after the window: nothing in or before it, but a history all the same.
    assert facts_by_asset[ids["after_only"]] == PriceWindowFacts(
        first_quote=None,
        last_quote=None,
        last_quote_before_start=None,
        quotes_in_window=0,
        fx_available=True,
        first_quote_in_window=None,
        first_quote_ever=LOADER_END + days(10),
        last_quote_ever=LOADER_END + days(20),
    )


@pytest.mark.asyncio
async def test_price_window_facts_need_a_rate_at_both_ends_of_the_window(window_assets):
    ids = window_assets.ids
    rate_ids: list[int] = []

    async def read() -> dict[int, PriceWindowFacts]:
        async with session() as db:
            return await load_price_window_facts(
                db,
                asset_ids=[ids["no_rate"], ids["probed"], ids["full"]],
                window_start=LOADER_START,
                window_end=LOADER_END,
                target_currency="EUR",
            )

    async def store_rate(day: date) -> None:
        async with session() as db:
            rate = FxRate(base=PROBED_CURRENCY, quote="EUR", date=day, rate=Decimal("0.02"), source="MANUAL")
            db.add(rate)
            await db.commit()
            rate_ids.append(rate.id)

    try:
        # Neither foreign currency has a rate yet; the asset quoted in the target needs none.
        before_any_rate = await read()
        assert before_any_rate[ids["no_rate"]].fx_available is False
        assert before_any_rate[ids["no_rate"]].quotes_in_window == len(every_day(LOADER_START, LOADER_END))
        assert before_any_rate[ids["probed"]].fx_available is False
        assert before_any_rate[ids["full"]].fx_available is True

        # A rate from inside the window converts the end but not the start.
        await store_rate(LOADER_START + days(5))
        assert (await read())[ids["probed"]].fx_available is False

        # A rate from before the window converts both ends.
        await store_rate(LOADER_START - days(3))
        after_both = await read()
        assert after_both[ids["probed"]].fx_available is True
        assert after_both[ids["no_rate"]].fx_available is False
    finally:
        # Whoever writes, cleans up: only the rates this test stored.
        async with session() as db:
            await db.execute(delete(FxRate).where(FxRate.id.in_(rate_ids)))
            await db.commit()


@pytest.mark.asyncio
async def test_holiday_carries_in_stored_prices_do_not_degrade_the_series(window_assets):
    ids = window_assets.ids

    async with session() as db:
        prepared = await RiskService(db)._prepare_asset_series(
            asset_ids=(ids["early"], ids["holiday"]),
            date_range=DateRangeModel(start=CRISIS_START, end=CRISIS_END),
            target_currency="EUR",
        )

    holiday = next(item for item in prepared.series if item.valuations.asset_id == ids["holiday"])
    carried = {point.valuation_date: (point.valuation_date - point.effective_price_date).days for point in holiday.valuations.points[1:] if point.is_price_carried_forward}
    # The holidays are carried — one day, and three over a weekend — and still ordinary.
    assert carried == {CRISIS_START + days(10): 1, CRISIS_START + days(21): 3}
    assert prepared.data_quality.carried_forward_price_points == 0
    assert prepared.data_quality.data_quality_status == DataQualityStatus.OK


def crisis_replay_request(asset_ids: list[int], replay_range: tuple[date, date] = (CRISIS_START, CRISIS_END)) -> RiskQueryRequest:
    """A historical replay of the crisis (or of a part of it) for an asset set, analysed over its last month."""
    return RiskQueryRequest.model_validate(
        {
            "scope": {"kind": "asset_set", "asset_ids": asset_ids},
            "date_range": {"start": (CRISIS_START + days(28)).isoformat(), "end": CRISIS_END.isoformat()},
            "target_currency": "EUR",
            "mode": "current_composition",
            "composition_policy": "current_buy_and_hold",
            "analytics": [
                {
                    "instance_id": "crisis",
                    "analytic_code": "stress",
                    "parameters": {
                        "method": "historical_replay",
                        "replay_range": {"start": replay_range[0].isoformat(), "end": replay_range[1].isoformat()},
                    },
                }
            ],
        }
    )


@pytest.mark.asyncio
async def test_a_late_starter_no_longer_shortens_the_replay_of_the_others(window_assets):
    ids, names = window_assets.ids, window_assets.names

    async with session() as db:
        response = await RiskService(db).execute(user_id=1, request=crisis_replay_request([ids["early"], ids["holiday"], ids["late"]]))

    (result,) = response.items
    assert result.output is not None, result.error
    # The replay spans the whole crisis: its baseline is the last quote before it and its first
    # return the crisis' first day. Kept in, the late starter would have moved both past its own
    # first quote, fifteen days in, for every asset.
    assert result.metadata.analyzed_range == DateRangeModel(start=CRISIS_START, end=CRISIS_END)
    assert result.status == RiskResultStatus.PARTIAL
    assert [(item.asset_id, item.reason, item.weight, item.treatment) for item in result.metadata.historical_replay_audit.excluded_assets] == [
        (ids["late"], Excluded.STARTS_AFTER_WINDOW_START, None, RiskHistoricalReplayExclusionTreatment.OMITTED_FROM_REPLAY),
    ]
    impacts = {impact.asset_id: impact for impact in result.output.impacts}
    assert set(impacts) == {ids["early"], ids["holiday"]}
    assert impacts[ids["early"]].return_source_asset_id == ids["early"]
    # Buy and hold from the Friday before the crisis to its last day.
    assert impacts[ids["early"]].shock_return == pytest.approx(float(close("early", CRISIS_END) / close("early", CRISIS_START - days(3)) - 1))

    exclusion_warnings = [warning for warning in result.warnings if warning.code == "historical_replay_assets_excluded"]
    assert [(warning.message_i18n_key, warning.details["asset_ids"], warning.message_params) for warning in exclusion_warnings] == [
        ("risk.warnings.historical_replay_excluded_starts_late", [ids["late"]], {"treatment": "omitted_from_replay", "names": names["late"], "count": 1}),
    ]
    # The exclusion is the only degradation: the holiday carries leave the data quality intact.
    assert result.data_quality.data_quality_status == DataQualityStatus.OK
    assert "data_quality_degraded" not in {warning.code for warning in result.warnings}


@pytest.mark.asyncio
async def test_a_gap_across_the_replay_start_is_stale_at_the_start_not_a_late_starter(window_assets):
    ids, names = window_assets.ids, window_assets.names

    # The loader reads the asset's first quote ever (up to the window end), not its first inside the
    # window: that is what tells an old history with a gap from a listing.
    async with session() as db:
        window_facts = await load_price_window_facts(
            db,
            asset_ids=[ids["gapped"], ids["late"]],
            window_start=CRISIS_START,
            window_end=CRISIS_END,
            target_currency="EUR",
        )
    assert (window_facts[ids["gapped"]].first_quote, window_facts[ids["gapped"]].last_quote_before_start) == (GAP_FIRST_QUOTE, GAP_LAST_QUOTE_BEFORE)
    assert (window_facts[ids["late"]].first_quote, window_facts[ids["late"]].last_quote_before_start) == (LATE_FIRST_QUOTE, None)

    async with session() as db:
        response = await RiskService(db).execute(user_id=1, request=crisis_replay_request([ids["early"], ids["gapped"], ids["late"]]))

    (result,) = response.items
    assert result.output is not None, result.error
    # Quoting again two days in does not rescue the gap: only a new listing gets that tolerance.
    expected_exclusions = sorted([(ids["gapped"], Excluded.STALE_AT_WINDOW_START), (ids["late"], Excluded.STARTS_AFTER_WINDOW_START)])
    assert [(item.asset_id, item.reason) for item in result.metadata.historical_replay_audit.excluded_assets] == expected_exclusions
    assert {impact.asset_id for impact in result.output.impacts} == {ids["early"]}
    assert result.metadata.analyzed_range == DateRangeModel(start=CRISIS_START, end=CRISIS_END)

    by_reason = {warning.details["reason"]: warning for warning in result.warnings if warning.code == "historical_replay_assets_excluded"}
    assert set(by_reason) == {"stale_at_window_start", "starts_after_window_start"}
    stale = by_reason["stale_at_window_start"]
    assert stale.message_i18n_key == "risk.warnings.historical_replay_excluded_stale_at_start"
    assert stale.details["asset_ids"] == [ids["gapped"]]
    assert stale.message_params == {"treatment": "omitted_from_replay", "days": STALE_PRICE_THRESHOLD_DAYS, "names": names["gapped"], "count": 1}
    late = by_reason["starts_after_window_start"]
    assert late.message_i18n_key == "risk.warnings.historical_replay_excluded_starts_late"
    assert late.message_params == {"treatment": "omitted_from_replay", "names": names["late"], "count": 1}


# ---------------------------------------------------------------------------
# Proposals through the service, on stored rows. A spy on the loader counts the readings: each
# proposal is verified on a second reading of the facts before it is offered, and no reading is
# spent when there is nothing to verify.
# ---------------------------------------------------------------------------


@pytest.fixture
def loader_calls(monkeypatch):
    calls: list[dict] = []
    real_loader = risk_service_module.load_price_window_facts

    async def spy(db, **kwargs):
        calls.append({"asset_ids": set(kwargs["asset_ids"]), "window": (kwargs["window_start"], kwargs["window_end"])})
        return await real_loader(db, **kwargs)

    monkeypatch.setattr(risk_service_module, "load_price_window_facts", spy)
    return calls


async def eligibility(asset_ids: list[int], start: date = ANALYSIS_START, end: date = ANALYSIS_END) -> RiskEligibilityResponse:
    async with session() as db:
        return await RiskService(db).asset_eligibility(RiskEligibilityRequest(asset_ids=asset_ids, date_range=DateRangeModel(start=start, end=end), target_currency="EUR"))


def verdicts(response: RiskEligibilityResponse, ids: dict[str, int], *keys: str) -> dict[str, tuple[str, list[str]]]:
    by_id = {item.asset_id: item for item in response.items}
    return {key: (by_id[ids[key]].level.value, [reason.value for reason in by_id[ids[key]].reasons]) for key in keys}


def as_range(start: date, end: date) -> DateRangeModel:
    return DateRangeModel(start=start, end=end)


@pytest.mark.parametrize(
    ("troubled", "verdict", "common", "suggested"),
    [
        # The period trimmed to the common span, starting the day after the latest first quote.
        pytest.param("a_late", ("warning", ["starts_late"]), (ANALYSIS_LATE_FIRST, HISTORY_LAST), (ANALYSIS_LATE_FIRST + days(1), ANALYSIS_END), id="trim-the-start"),
        pytest.param("a_ends", ("warning", ["stale_at_end"]), (HISTORY_FIRST, ANALYSIS_ENDS), (ANALYSIS_START, ANALYSIS_ENDS), id="trim-the-end"),
        # A period that misses the common span is shifted onto it.
        pytest.param("a_after", ("ineligible", ["no_prices"]), (ANALYSIS_AFTER_FIRST, HISTORY_LAST), (ANALYSIS_AFTER_FIRST + days(1), HISTORY_LAST), id="shift-a-disjoint-period"),
    ],
)
@pytest.mark.asyncio
async def test_a_period_reason_of_a_quoted_asset_gets_a_verified_common_period(window_assets, loader_calls, troubled, verdict, common, suggested):
    ids = window_assets.ids

    response = await eligibility([ids["a_full"], ids[troubled]])

    assert verdicts(response, ids, "a_full", troubled) == {"a_full": ("eligible", []), troubled: verdict}
    assert response.common_range == as_range(*common)
    assert response.suggested_range == as_range(*suggested)
    # One reading for the period, one to verify the proposal.
    assert [call["window"] for call in loader_calls] == [(ANALYSIS_START, ANALYSIS_END), suggested]


@pytest.mark.asyncio
async def test_a_trimmed_period_too_short_for_the_quote_floor_falls_back_to_the_common_span(window_assets, loader_calls):
    ids = window_assets.ids

    response = await eligibility([ids["a_thin_after"], ids["a_late"]])

    # Daily in March, weekly after: eligible in the period, 13 quotes once trimmed, 39 in the span.
    assert verdicts(response, ids, "a_thin_after", "a_late") == {"a_thin_after": ("eligible", []), "a_late": ("warning", ["starts_late"])}
    span = (ANALYSIS_LATE_FIRST + days(1), date(2014, 12, 29))
    assert response.common_range == as_range(ANALYSIS_LATE_FIRST, date(2014, 12, 29))
    assert response.suggested_range == as_range(*span)
    assert [call["window"] for call in loader_calls] == [(ANALYSIS_START, ANALYSIS_END), (span[0], ANALYSIS_END), span]


@pytest.mark.parametrize(
    ("listing", "first_quote", "candidates"),
    [
        # Eleven quotes in the period: the trimmed period holds even fewer, so it is read in vain
        # before the span.
        pytest.param("a_late_thin", date(2014, 6, 20), ((date(2014, 6, 21), ANALYSIS_END), (date(2014, 6, 21), HISTORY_LAST)), id="eleven-quotes-in-the-period"),
        # Two quotes, from the day before the end: the trimmed period is empty, the span is read at once.
        pytest.param("a_late_last_day", ANALYSIS_END - days(1), ((ANALYSIS_END, HISTORY_LAST),), id="two-quotes-from-the-day-before-the-end"),
    ],
)
@pytest.mark.asyncio
async def test_a_late_listing_short_of_the_quote_floor_gets_the_common_span(window_assets, loader_calls, listing, first_quote, candidates):
    ids = window_assets.ids

    response = await eligibility([ids["a_full"], ids[listing]])

    # Blocked by too few quotes, the listing reports no late start...
    assert verdicts(response, ids, "a_full", listing) == {"a_full": ("eligible", []), listing: ("ineligible", ["too_few_quotes"])}
    # ...yet the period is what leaves it short: the span from the day after its first quote mends it.
    assert response.common_range == as_range(first_quote, HISTORY_LAST)
    assert response.suggested_range == as_range(first_quote + days(1), HISTORY_LAST)
    assert [call["window"] for call in loader_calls] == [(ANALYSIS_START, ANALYSIS_END), *candidates]


@pytest.mark.asyncio
async def test_no_proposal_when_no_candidate_meets_the_quote_floor(window_assets, loader_calls):
    ids = window_assets.ids

    response = await eligibility([ids["a_weekly"], ids["a_late_short"]])

    assert verdicts(response, ids, "a_weekly", "a_late_short") == {"a_weekly": ("ineligible", ["too_few_quotes"]), "a_late_short": ("warning", ["starts_late"])}
    common = (date(2014, 6, 1), date(2014, 7, 10))
    assert response.common_range == as_range(*common)
    # Both candidates were read and both leave the weekly asset under the floor (4 and 5 quotes).
    candidates = suggested_analysis_ranges(common, ANALYSIS_START, ANALYSIS_END)
    assert candidates == ((date(2014, 6, 2), ANALYSIS_END), (date(2014, 6, 2), date(2014, 7, 10)))
    assert [call["window"] for call in loader_calls] == [(ANALYSIS_START, ANALYSIS_END), *candidates]
    assert response.suggested_range is None


@pytest.mark.asyncio
async def test_no_proposal_while_fx_is_missing_at_an_end_of_the_candidate(window_assets, loader_calls):
    ids = window_assets.ids
    span = (date(2014, 1, 6), date(2014, 6, 30))
    rate_ids: list[int] = []

    async def store_rate(day: date) -> None:
        async with session() as db:
            rate = FxRate(base="EUR", quote=ANALYSIS_FX_CURRENCY, date=day, rate=Decimal("400"), source="MANUAL")
            db.add(rate)
            await db.commit()
            rate_ids.append(rate.id)

    try:
        # A rate from August converts the autumn period, not the earlier common span.
        await store_rate(date(2014, 8, 1))
        response = await eligibility([ids["a_before"], ids["a_ngn"]], FX_PERIOD_START, FX_PERIOD_END)

        assert verdicts(response, ids, "a_before", "a_ngn") == {"a_before": ("ineligible", ["no_prices"]), "a_ngn": ("eligible", [])}
        assert response.common_range == as_range(date(2014, 1, 5), date(2014, 6, 30))
        assert [call["window"] for call in loader_calls] == [(FX_PERIOD_START, FX_PERIOD_END), span]
        assert response.suggested_range is None

        # Control: with a rate from before the span, the very same candidate is offered.
        await store_rate(date(2013, 12, 31))
        assert (await eligibility([ids["a_before"], ids["a_ngn"]], FX_PERIOD_START, FX_PERIOD_END)).suggested_range == as_range(*span)
    finally:
        # Whoever writes, cleans up: only the rates this test stored.
        async with session() as db:
            await db.execute(delete(FxRate).where(FxRate.id.in_(rate_ids)))
            await db.commit()


@pytest.mark.parametrize(
    ("assets", "verdict", "common"),
    [
        pytest.param(("a_full", "a_starts3"), {"a_full": ("eligible", []), "a_starts3": ("eligible", [])}, (ANALYSIS_START + days(3), HISTORY_LAST), id="every-asset-eligible"),
        pytest.param(("a_full", "a_never"), {"a_full": ("eligible", []), "a_never": ("ineligible", ["no_price_history"])}, (HISTORY_FIRST, HISTORY_LAST), id="only-an-asset-never-quoted"),
        # Inside the common span, a stale end is a gap in the asset's quotes: no span mends it.
        pytest.param(("a_full", "a_gap_end"), {"a_full": ("eligible", []), "a_gap_end": ("warning", ["stale_at_end"])}, (HISTORY_FIRST, HISTORY_LAST), id="period-inside-the-span-with-a-gap"),
    ],
)
@pytest.mark.asyncio
async def test_no_proposal_is_computed_when_no_period_helps(window_assets, loader_calls, assets, verdict, common):
    ids = window_assets.ids

    response = await eligibility([ids[key] for key in assets])

    assert verdicts(response, ids, *assets) == verdict
    # The common span is still reported, the proposal is not, and no second reading is spent.
    assert response.common_range == as_range(*common)
    assert response.suggested_range is None
    assert len(loader_calls) == 1


@pytest.mark.parametrize(
    ("troubled", "reason"),
    [
        pytest.param("a_weekly", "too_few_quotes", id="too-few-quotes-alone"),
        pytest.param("a_kes", "missing_fx", id="missing-fx-alone"),
        pytest.param("a_never", "no_price_history", id="no-price-history-alone"),
    ],
)
@pytest.mark.asyncio
async def test_reasons_a_period_cannot_mend_never_trigger_a_proposal(window_assets, loader_calls, troubled, reason):
    ids = window_assets.ids
    scope = [ids[troubled], ids["a_starts3"]]

    # The premise, read from the facts rather than the reasons: each asset is either never quoted or
    # quoted from (at most three days after) the start of the period to its end, so the period
    # leaves none of them short.
    async with session() as db:
        window_facts = await load_price_window_facts(db, asset_ids=scope, window_start=ANALYSIS_START, window_end=ANALYSIS_END, target_currency="EUR")
    assert not any(period_limits_coverage(item, ANALYSIS_START, ANALYSIS_END) for item in window_facts.values())

    response = await eligibility(scope)

    assert verdicts(response, ids, troubled, "a_starts3") == {troubled: ("ineligible", [reason]), "a_starts3": ("eligible", [])}
    # Candidates exist — the asset quoted from three days in makes the period differ from the span —
    # so what stops the proposal is the premise above, not the absence of a candidate.
    common = (response.common_range.start, response.common_range.end)
    assert suggested_analysis_ranges(common, ANALYSIS_START, ANALYSIS_END) != ()
    assert response.suggested_range is None
    assert len(loader_calls) == 1


def replay_audit(response):
    (result,) = response.items
    assert result.output is not None, result.error
    return result, result.metadata.historical_replay_audit


async def replay(asset_ids: list[int], replay_range: tuple[date, date] = (CRISIS_START, CRISIS_END)):
    async with session() as db:
        return await RiskService(db).execute(user_id=1, request=crisis_replay_request(asset_ids, replay_range))


@pytest.mark.asyncio
async def test_a_replay_proposal_is_offered_once_a_second_reading_confirms_it(window_assets, loader_calls):
    ids = window_assets.ids
    proposed = (LATE_FIRST_QUOTE + days(1), CRISIS_END)

    _result, audit = replay_audit(await replay([ids["early"], ids["holiday"], ids["late"], ids["empty"]]))

    assert {(item.asset_id, item.reason) for item in audit.excluded_assets} == {(ids["late"], Excluded.STARTS_AFTER_WINDOW_START), (ids["empty"], Excluded.NO_PRICES_IN_WINDOW)}
    assert audit.suggested_range == as_range(*proposed)
    assert audit.suggested_range_recovers == [ids["late"]]
    # The second reading covers the proposed window, for the covered assets and the recovered one;
    # the asset with no prices is not in it, since no shorter window brings it back.
    assert loader_calls[1:] == [{"asset_ids": {ids["early"], ids["holiday"], ids["late"]}, "window": proposed}]


@pytest.mark.asyncio
async def test_a_replay_proposal_is_dropped_when_a_covered_sparse_asset_would_lose_its_start_price(window_assets, loader_calls):
    ids = window_assets.ids
    proposed = (LATE_FIRST_QUOTE + days(1), CRISIS_END)

    _result, audit = replay_audit(await replay([ids["early"], ids["sparse"], ids["late"]]))

    # Priced three days before the crisis, the sparse asset is covered by it...
    assert [(item.asset_id, item.reason) for item in audit.excluded_assets] == [(ids["late"], Excluded.STARTS_AFTER_WINDOW_START)]
    # ...but not by the proposal, which would start 19 days after that price: checked, then dropped.
    assert [call["window"] for call in loader_calls] == [(CRISIS_START, CRISIS_END), proposed]
    assert audit.suggested_range is None
    assert audit.suggested_range_recovers == []


@pytest.mark.asyncio
async def test_replay_proposal_recovers_are_ordered_by_asset(window_assets):
    ids = window_assets.ids

    _result, audit = replay_audit(await replay([ids["gapped"], ids["late"], ids["early"]]))

    # The listing sets the start; by then the gapped asset quotes again, so both come back.
    assert audit.suggested_range == as_range(LATE_FIRST_QUOTE + days(1), CRISIS_END)
    assert audit.suggested_range_recovers == sorted([ids["gapped"], ids["late"]])


@pytest.mark.parametrize("keys", [pytest.param(("early", "holiday"), id="nothing-excluded"), pytest.param(("early", "empty"), id="only-a-no-prices-exclusion")])
@pytest.mark.asyncio
async def test_a_replay_without_edge_exclusions_reads_the_window_facts_once(window_assets, loader_calls, keys):
    ids = window_assets.ids

    _result, audit = replay_audit(await replay([ids[key] for key in keys]))

    assert audit.suggested_range is None
    assert len(loader_calls) == 1


@pytest.mark.parametrize(
    ("key", "first_in_window"),
    [pytest.param("late", LATE_FIRST_QUOTE, id="listing"), pytest.param("gapped", GAP_RESUMES, id="gap-at-the-start")],
)
@pytest.mark.asyncio
async def test_replaying_the_proposed_range_brings_the_recovered_asset_back(window_assets, key, first_in_window):
    ids = window_assets.ids
    scope = [ids["early"], ids[key]]
    proposed = (first_in_window + days(1), CRISIS_END)

    _result, audit = replay_audit(await replay(scope))
    assert [item.asset_id for item in audit.excluded_assets] == [ids[key]]
    assert audit.suggested_range is not None
    assert audit.suggested_range_recovers == [ids[key]]
    offered = (audit.suggested_range.start, audit.suggested_range.end)

    # Replay whatever was offered: the asset is back, the other one kept, nothing excluded...
    result, audit = replay_audit(await replay(scope, offered))
    assert audit.excluded_assets == []
    assert (audit.suggested_range, audit.suggested_range_recovers) == (None, [])
    assert {impact.asset_id for impact in result.output.impacts} == set(scope)
    # ...and the first quote in the window is the starting price: the baseline precedes the range.
    unwanted = {"baseline_inside_requested_range", f"short_history:{ids[key]}"}
    assert unwanted.isdisjoint(result.data_quality.warnings)
    # The offer is the day after the first quote in the window.
    assert offered == proposed
    async with session() as db:
        prepared = await RiskService(db)._prepare_asset_series(asset_ids=tuple(scope), date_range=as_range(*proposed), target_currency="EUR")
        on_first_quote = await RiskService(db)._prepare_asset_series(asset_ids=tuple(scope), date_range=as_range(first_in_window, CRISIS_END), target_currency="EUR")
        facts_on_first_quote = await load_price_window_facts(db, asset_ids=[ids[key]], window_start=first_in_window, window_end=CRISIS_END, target_currency="EUR")
    assert prepared.baseline_date == first_in_window
    assert unwanted.isdisjoint(prepared.warnings)

    # Control — starting ON the first quote instead: a listing gets a baseline inside the range, a
    # gapped asset has no recent price before it and is excluded again.
    if key == "late":
        assert unwanted <= set(on_first_quote.warnings)
    else:
        assert replay_coverage(facts_on_first_quote[ids[key]], first_in_window, CRISIS_END) == Excluded.STALE_AT_WINDOW_START


@pytest.mark.parametrize(
    ("key", "proposed"),
    [
        pytest.param("late", (LATE_FIRST_QUOTE + days(1), CRISIS_END), id="listing"),
        pytest.param("gapped", (GAP_RESUMES + days(1), CRISIS_END), id="gap-at-the-start"),
    ],
)
@pytest.mark.asyncio
async def test_a_replay_left_empty_by_its_edges_is_unavailable_with_the_proposal(window_assets, key, proposed):
    ids = window_assets.ids

    (result,) = (await replay([ids[key]])).items

    # No audit to carry the proposal: the error does, since this is when it matters most.
    assert result.status == RiskResultStatus.UNAVAILABLE
    assert result.error.code == RiskErrorCode.INSUFFICIENT_HISTORY
    assert result.error.details == {
        "excluded_asset_ids": [ids[key]],
        "suggested_range": {"start": proposed[0].isoformat(), "end": proposed[1].isoformat()},
        "suggested_range_recovers": [ids[key]],
    }


@pytest.mark.asyncio
async def test_a_replay_of_assets_never_priced_in_the_window_is_unavailable_without_a_proposal(window_assets):
    ids = window_assets.ids

    (result,) = (await replay([ids["empty"], ids["after_only"]])).items

    assert result.status == RiskResultStatus.UNAVAILABLE
    assert result.error.code == RiskErrorCode.INSUFFICIENT_HISTORY
    assert result.error.details == {"excluded_asset_ids": sorted([ids["empty"], ids["after_only"]])}


# ---------------------------------------------------------------------------
# Market-closed repeats are no quotes (developer's decision of 30/09/2026)
#
# A source such as justETF stores a row for every calendar day, repeating the last close on a weekend
# or an exchange holiday. A row on a weekend or a market holiday with exactly the close of the row
# before it is a carry: the facts count and date genuine quotes only. A weekend move is a quote, a
# flat weekday too, and so is the first row of a history, which has no row before it.
#
# Easter 2025 stored the justETF way: Good Friday and Easter Monday repeat Thursday's close. Every
# close is a multiple of 0.25, so a repeat is exact however the column stores it.
# ---------------------------------------------------------------------------

EASTER_2025 = frozenset({date(2025, 4, 18), date(2025, 4, 21)})
SEVEN_DAY_FIRST = date(2025, 4, 5)  # a Saturday, and the first row of every history below
SEVEN_DAY_LAST = date(2025, 5, 4)  # a Sunday
THREE_WEEKS = (date(2025, 4, 7), date(2025, 4, 27))  # Monday to Sunday


def seven_day_closes(*, closed_weekdays: frozenset[date] = frozenset(), weekend_moves: frozenset[date] = frozenset()) -> dict[date, Decimal]:
    """A row every calendar day: weekdays move, a weekend or a closed weekday repeats the row before."""
    closes: dict[date, Decimal] = {}
    previous: Decimal | None = None
    for day in every_day(SEVEN_DAY_FIRST, SEVEN_DAY_LAST):
        moving = Decimal("100") + Decimal((day - SEVEN_DAY_FIRST).days) / 2
        if previous is None:
            value = moving
        elif day in weekend_moves:
            value = previous + Decimal("0.25")
        elif day.weekday() >= 5 or day in closed_weekdays:
            value = previous
        else:
            value = moving
        closes[day] = value
        previous = value
    return closes


SEVEN_DAY_ASSETS: dict[str, dict[date, Decimal]] = {
    "etf": seven_day_closes(closed_weekdays=EASTER_2025),
    # Saturday 12 moves; Sunday 13 repeats Saturday — the row before it, not Friday's.
    "weekend_move": seven_day_closes(closed_weekdays=EASTER_2025, weekend_moves=frozenset({date(2025, 4, 12)})),
    "crypto": {day: Decimal("300") + Decimal((day - SEVEN_DAY_FIRST).days) * Decimal("0.75") for day in every_day(SEVEN_DAY_FIRST, SEVEN_DAY_LAST)},
}


@pytest.fixture(scope="module")
def seven_day_assets():
    marker = uuid4().hex

    async def setup() -> dict[str, int]:
        async with session() as db:
            assets = {key: Asset(display_name=f"Seven-day {key} {marker}", currency="EUR", asset_type=AssetType.STOCK, active=True) for key in SEVEN_DAY_ASSETS}
            db.add_all(assets.values())
            await db.flush()
            db.add_all(PriceHistory(asset_id=assets[key].id, date=day, close=value, currency="EUR", source_plugin_key="seven_day_test") for key, closes in SEVEN_DAY_ASSETS.items() for day, value in closes.items())
            await db.commit()
            return {key: asset.id for key, asset in assets.items()}

    async def cleanup(ids: dict[str, int]) -> None:
        async with session() as db:
            owned = list(ids.values())
            await db.execute(delete(PriceHistory).where(PriceHistory.asset_id.in_(owned)))
            await db.execute(delete(Asset).where(Asset.id.in_(owned)))
            await db.commit()

    ids = asyncio.run(setup())
    yield ids
    asyncio.run(cleanup(ids))


async def seven_day_facts(ids: dict[str, int], key: str, window: tuple[date, date], market_holidays: frozenset[date] | None = None) -> PriceWindowFacts:
    """One asset's facts over one window; the holiday table is passed only when a test gives one."""
    table = {} if market_holidays is None else {"market_holidays": market_holidays}
    async with session() as db:
        facts_by_asset = await load_price_window_facts(db, asset_ids=[ids[key]], window_start=window[0], window_end=window[1], target_currency="EUR", **table)
    return facts_by_asset[ids[key]]


@pytest.mark.asyncio
async def test_weekend_repeats_are_carries_not_quotes_in_the_window_facts(seven_day_assets):
    crypto = await seven_day_facts(seven_day_assets, "crypto", THREE_WEEKS)
    etf = await seven_day_facts(seven_day_assets, "etf", THREE_WEEKS)

    # Control, from the same loader: a series that moves every day keeps every row as a quote.
    assert crypto == PriceWindowFacts(
        first_quote=date(2025, 4, 5),
        last_quote=date(2025, 4, 27),
        last_quote_before_start=date(2025, 4, 6),
        quotes_in_window=21,
        fx_available=True,
        first_quote_in_window=date(2025, 4, 7),
        first_quote_ever=date(2025, 4, 5),
        last_quote_ever=date(2025, 5, 4),
    )
    # The seven-day ETF is quoted on weekdays only. Without a holiday table, Good Friday and Easter
    # Monday are flat weekdays, so quotes. The first row, a Saturday, has no row before it: a quote.
    assert etf == PriceWindowFacts(
        first_quote=date(2025, 4, 5),
        last_quote=date(2025, 4, 25),
        last_quote_before_start=date(2025, 4, 5),
        quotes_in_window=15,
        fx_available=True,
        first_quote_in_window=date(2025, 4, 7),
        first_quote_ever=date(2025, 4, 5),
        last_quote_ever=date(2025, 5, 2),
    )


@pytest.mark.asyncio
async def test_a_window_ending_on_sunday_ends_on_fridays_quote_and_one_starting_on_saturday_begins_on_monday(seven_day_assets):
    ending_on_sunday = await seven_day_facts(seven_day_assets, "etf", (date(2025, 4, 7), date(2025, 4, 13)))
    assert (ending_on_sunday.last_quote, ending_on_sunday.quotes_in_window) == (date(2025, 4, 11), 5)

    starting_on_saturday = await seven_day_facts(seven_day_assets, "etf", (date(2025, 4, 12), date(2025, 4, 20)))
    assert starting_on_saturday.first_quote_in_window == date(2025, 4, 14)
    assert starting_on_saturday.last_quote_before_start == date(2025, 4, 11)
    # Monday 14 to Good Friday, a flat weekday without the holiday table.
    assert (starting_on_saturday.last_quote, starting_on_saturday.quotes_in_window) == (date(2025, 4, 18), 5)


@pytest.mark.asyncio
async def test_a_weekend_move_is_a_quote_and_the_repeat_after_it_is_not(seven_day_assets):
    three_weeks = await seven_day_facts(seven_day_assets, "weekend_move", THREE_WEEKS)
    # The fifteen weekdays, and Saturday 12, which moved.
    assert three_weeks.quotes_in_window == 16

    first_week = await seven_day_facts(seven_day_assets, "weekend_move", (date(2025, 4, 7), date(2025, 4, 13)))
    # Sunday 13 repeats Saturday's close, the row before it: a carry, although it differs from Friday's.
    assert (first_week.last_quote, first_week.quotes_in_window) == (date(2025, 4, 12), 6)


@pytest.mark.asyncio
async def test_a_repeat_on_a_market_holiday_is_a_carry_and_a_move_on_it_is_a_quote(seven_day_assets):
    three_weeks = await seven_day_facts(seven_day_assets, "etf", THREE_WEEKS, EASTER_2025)
    # Good Friday and Easter Monday repeat Thursday's close: carries once they are holidays.
    assert (three_weeks.quotes_in_window, three_weeks.last_quote) == (13, date(2025, 4, 25))

    easter_week = await seven_day_facts(seven_day_assets, "etf", (date(2025, 4, 14), date(2025, 4, 20)), EASTER_2025)
    assert (easter_week.last_quote, easter_week.quotes_in_window) == (date(2025, 4, 17), 4)

    after_easter = await seven_day_facts(seven_day_assets, "etf", (date(2025, 4, 19), THREE_WEEKS[1]), EASTER_2025)
    assert (after_easter.last_quote_before_start, after_easter.first_quote_in_window, after_easter.quotes_in_window) == (date(2025, 4, 17), date(2025, 4, 22), 4)

    # The crypto moved over Easter: a move on a holiday is a quote.
    crypto = await seven_day_facts(seven_day_assets, "crypto", THREE_WEEKS, EASTER_2025)
    assert crypto.quotes_in_window == 21

    # Control: without the holiday table, the very same Good Friday row is a flat weekday, and a quote.
    no_table = await seven_day_facts(seven_day_assets, "etf", (date(2025, 4, 14), date(2025, 4, 20)))
    assert (no_table.last_quote, no_table.quotes_in_window) == (date(2025, 4, 18), 5)


@pytest.mark.asyncio
async def test_twenty_calendar_days_of_a_seven_day_source_are_too_few_quotes(seven_day_assets, monkeypatch):
    period = (date(2025, 4, 7), date(2025, 4, 26))  # Monday to Saturday: twenty rows
    etf = await seven_day_facts(seven_day_assets, "etf", period)
    crypto = await seven_day_facts(seven_day_assets, "crypto", period)

    # Twenty rows each: fifteen quotes for the ETF, twenty for the crypto.
    assert (etf.quotes_in_window, crypto.quotes_in_window) == (15, 20)
    assert analysis_eligibility(etf, *period) == (Level.INELIGIBLE, (Why.TOO_FEW_QUOTES,))
    assert analysis_eligibility(crypto, *period) == (Level.ELIGIBLE, ())

    # Through the service, which reads the facts with the holiday table it awaits: Easter takes two more.
    async def easter_table() -> frozenset[date]:
        return EASTER_2025

    monkeypatch.setattr(risk_service_module, "ensure_market_holidays", easter_table, raising=False)
    response = await eligibility([seven_day_assets["etf"], seven_day_assets["crypto"]], *period)

    by_id = {item.asset_id: item for item in response.items}
    etf_item, crypto_item = by_id[seven_day_assets["etf"]], by_id[seven_day_assets["crypto"]]
    assert (etf_item.level, etf_item.reasons, etf_item.quotes_in_period, etf_item.last_quote) == (Level.INELIGIBLE, [Why.TOO_FEW_QUOTES], 13, date(2025, 4, 25))
    assert (crypto_item.level, crypto_item.quotes_in_period) == (Level.ELIGIBLE, 20)


# ---------------------------------------------------------------------------
# One holiday table per request, handed to every reading of it (developer's decision of 30/09/2026)
#
# The service awaits `ensure_market_holidays()` once per request and passes the table to every
# `load_price_window_facts` and `prepare_asset_series_set` it runs. The table served below is a date
# nothing here is quoted near, so it moves no number: only the plumbing is observed.
# ---------------------------------------------------------------------------

NOT_PASSED = object()


@pytest.fixture
def holiday_table_plumbing(monkeypatch):
    table = frozenset({date(1999, 12, 31)})
    seen: dict[str, list] = {"ensure": [], "loader": [], "prepare": []}
    real_loader = risk_service_module.load_price_window_facts
    real_prepare = risk_service_module.prepare_asset_series_set

    async def served_table() -> frozenset[date]:
        seen["ensure"].append(table)
        return table

    async def loader_spy(db, **kwargs):
        seen["loader"].append(kwargs.get("market_holidays", NOT_PASSED))
        return await real_loader(db, **kwargs)

    def prepare_spy(*args, **kwargs):
        seen["prepare"].append(kwargs.get("market_holidays", NOT_PASSED))
        return real_prepare(*args, **kwargs)

    monkeypatch.setattr(risk_service_module, "ensure_market_holidays", served_table, raising=False)
    monkeypatch.setattr(risk_service_module, "load_price_window_facts", loader_spy)
    monkeypatch.setattr(risk_service_module, "prepare_asset_series_set", prepare_spy)
    return table, seen


@pytest.mark.asyncio
async def test_a_replay_request_awaits_the_holiday_table_once_and_hands_it_to_every_reading(window_assets, holiday_table_plumbing):
    table, seen = holiday_table_plumbing
    ids = window_assets.ids

    _result, audit = replay_audit(await replay([ids["early"], ids["holiday"], ids["late"], ids["empty"]]))

    # Premise: this request reads the facts twice (the crisis window, then the proposal) and prepares
    # two series sets (the analysis period, then the replay window).
    assert audit.suggested_range is not None
    assert (len(seen["loader"]), len(seen["prepare"])) == (2, 2)
    assert len(seen["ensure"]) == 1
    assert seen["loader"] == [table, table]
    assert seen["prepare"] == [table, table]


@pytest.mark.asyncio
async def test_an_eligibility_request_awaits_the_holiday_table_once_for_both_readings(window_assets, holiday_table_plumbing):
    table, seen = holiday_table_plumbing
    ids = window_assets.ids

    response = await eligibility([ids["a_full"], ids["a_late"]])

    # Premise: a verified proposal, so the facts are read twice.
    assert response.suggested_range is not None
    assert len(seen["loader"]) == 2
    assert len(seen["ensure"]) == 1
    assert seen["loader"] == [table, table]
