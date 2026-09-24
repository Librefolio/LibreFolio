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
    RiskHistoricalReplayExclusionReason,
    RiskHistoricalReplayExclusionTreatment,
    RiskQueryRequest,
    RiskResultStatus,
)
from backend.app.services.data_quality_thresholds import RISK_MIN_OBSERVATIONS, STALE_PRICE_THRESHOLD_DAYS  # noqa: E402
from backend.app.services.risk.eligibility import (  # noqa: E402
    PriceWindowFacts,
    analysis_eligibility,
    load_price_window_facts,
    replay_coverage,
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


def facts(
    *,
    first: date | None = START,
    last: date | None = END,
    before: date | None = None,
    quotes: int = FLOOR,
    fx: bool = True,
) -> PriceWindowFacts:
    """Facts of an asset quoted from the start to the end of the window, unless told otherwise."""
    return PriceWindowFacts(first_quote=first, last_quote=last, last_quote_before_start=before, quotes_in_window=quotes, fx_available=fx)


# ---------------------------------------------------------------------------
# Analysis eligibility: the boundaries of each rule
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("window_facts", "expected"),
    [
        pytest.param(facts(first=None, last=None, quotes=0), (Level.INELIGIBLE, (Why.NO_PRICES,)), id="no-quote-at-all"),
        pytest.param(facts(first=START - days(90), last=START - days(30), before=START - days(30), quotes=0), (Level.INELIGIBLE, (Why.NO_PRICES,)), id="quoted-only-before-the-period"),
        pytest.param(facts(quotes=FLOOR - 1), (Level.INELIGIBLE, (Why.TOO_FEW_QUOTES,)), id="one-quote-short-of-the-floor"),
        pytest.param(facts(quotes=FLOOR), (Level.ELIGIBLE, ()), id="exactly-the-floor"),
        pytest.param(facts(fx=False), (Level.INELIGIBLE, (Why.MISSING_FX,)), id="missing-fx-alone"),
        pytest.param(facts(quotes=FLOOR - 1, fx=False), (Level.INELIGIBLE, (Why.TOO_FEW_QUOTES, Why.MISSING_FX)), id="missing-fx-with-too-few-quotes"),
        pytest.param(facts(first=None, last=None, quotes=0, fx=False), (Level.INELIGIBLE, (Why.NO_PRICES, Why.MISSING_FX)), id="missing-fx-with-no-prices"),
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


def every_day(first: date, last: date) -> list[date]:
    return [first + days(offset) for offset in range((last - first).days + 1)]


def weekdays(first: date, last: date, *, skip: frozenset[date] = frozenset()) -> list[date]:
    return [day for day in every_day(first, last) if day.weekday() < 5 and day not in skip]


ASSETS: dict[str, tuple[str, Decimal, list[date]]] = {
    # Loader: quotes around the window, one past its end.
    "full": ("EUR", Decimal("1"), [LOADER_START - days(10), LOADER_START - days(3), *every_day(LOADER_START, LOADER_END - days(2)), LOADER_END + days(5)]),
    "empty": ("EUR", Decimal("1"), []),
    "no_rate": (NO_RATE_CURRENCY, Decimal("1"), every_day(LOADER_START, LOADER_END)),
    "probed": (PROBED_CURRENCY, Decimal("1"), every_day(LOADER_START, LOADER_END)),
    # Replay: two assets quoted through the crisis, one that starts in the middle of it, and one
    # quoted long before it whose quotes pause across its start.
    "early": ("EUR", Decimal("0.5"), weekdays(CRISIS_START - days(14), CRISIS_END)),
    "holiday": ("EUR", Decimal("0.25"), weekdays(CRISIS_START - days(14), CRISIS_END, skip=HOLIDAYS)),
    "late": ("EUR", Decimal("1"), weekdays(LATE_FIRST_QUOTE, CRISIS_END)),
    "gapped": ("EUR", Decimal("0.75"), [*weekdays(GAP_FIRST_QUOTE, GAP_LAST_QUOTE_BEFORE), *weekdays(GAP_RESUMES, CRISIS_END)]),
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
            asset_ids=[ids["full"], ids["empty"], ids["full"]],
            window_start=LOADER_START,
            window_end=LOADER_END,
            target_currency="EUR",
        )

    assert set(facts_by_asset) == {ids["full"], ids["empty"]}
    # The quote past the end is not "the last quote on or before the end".
    assert facts_by_asset[ids["full"]] == PriceWindowFacts(
        first_quote=LOADER_START - days(10),
        last_quote=LOADER_END - days(2),
        last_quote_before_start=LOADER_START - days(3),
        quotes_in_window=len(every_day(LOADER_START, LOADER_END - days(2))),
        fx_available=True,
    )
    assert facts_by_asset[ids["empty"]] == PriceWindowFacts(first_quote=None, last_quote=None, last_quote_before_start=None, quotes_in_window=0, fx_available=True)


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


def crisis_replay_request(asset_ids: list[int]) -> RiskQueryRequest:
    """A historical replay of the crisis for an asset set, analysed over its last month."""
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
                        "replay_range": {"start": CRISIS_START.isoformat(), "end": CRISIS_END.isoformat()},
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
