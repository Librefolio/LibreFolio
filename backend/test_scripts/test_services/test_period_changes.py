"""MF-P2 — the fixed-period changes (1D … 5Y) of asset prices and FX rates, from the stored data through the services.

``services/assets/period_changes.get_period_changes_bulk`` values the days ``fixed_period_dates(as_of)`` names — the
last stored price on or before each, converted at that day's rate when a target currency is asked —, and
``services/fx/period_changes.get_fx_period_changes_bulk`` takes a pair's rate on each of them from ``convert_bulk``
(1 base → quote); both hand the values to the house's ``fixed_period_changes``. The house itself is pure and covered by
``test_financial_math/test_fixed_period_changes.py``: this file covers what only the database shows.

The point of the lot is a parity contract: the numbers equal what the pages show today.

- Assets: the page's ``computePeriodDelta`` (``frontend/src/lib/utils/assetPriceDerived.ts``, ported in
  ``fixtures/period_changes/page_ports.py``) on the dense series of the existing price query
  (``AssetSourceManager.get_prices_bulk``, the service behind ``POST /assets/prices/query``: backward-filled to the
  range end, each day converted at its own date) over ``[as_of − 5Y − 10 days, as_of]``; natively, and in a target
  currency whose rates move on days that have no price. ``change_ratio × 100`` must equal the port's percentage.
- FX: ``rate(as_of) / rate(as_of − N) − 1`` and ``rate(as_of − N) / rate(as_of) − 1`` against the seeded rates, and the
  FX page's own ``computePeriodDelta`` (``frontend/src/routes/(app)/fx/+page.svelte``) on the per-day conversions
  ``POST /fx/currencies/convert`` makes, which are ``convert_bulk`` of 1 base on every day of the range.
- What X pinned: the periods in display order (1D, 1W, 1M, 3M, 6M, 1Y, 2Y, 3Y, 5Y), ``days`` in each, ``1D`` included,
  and a 1D of exactly 0 over a weekend (Friday's price carried, ``as_of`` a Sunday).

Comparisons are exact: every seeded price and rate is 2^a·5^b (``fixtures/period_changes/seeds.py``), so each quotient
terminates and the service's ``last / ref − 1`` and the page's ``(last − ref) / ref`` are the same Decimal.

Isolation. The assets are this file's (unique names) and leave with their prices at the end. FX rates are global by
(date, pair): every pair here is one nothing else in the repository uses — AMD/BDT, AMD/SZL, AMD/LSL, BBD/BZD and the
never-seeded MVR/SCR — dated 1980-1987, and its rows are deleted before seeding (a killed run's leftovers) and after.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Asset, AssetType, FxRate, PriceHistory
from backend.app.db.session import get_async_engine
from backend.app.schemas.common import Currency, DateRangeModel
from backend.app.schemas.fx import FXPeriodChangesRequest, FXPeriodChangesResult
from backend.app.schemas.prices import FAPeriodChangesQueryItem, FAPeriodChangesResult, FAPriceQueryItem, FAPriceQueryResult
from backend.app.services.assets.manager import AssetSourceManager
from backend.app.services.assets.period_changes import get_period_changes_bulk
from backend.app.services.fx.conversion import convert_bulk
from backend.app.services.fx.period_changes import get_fx_period_changes_bulk
from backend.test_scripts.fixtures.period_changes.page_ports import PAGE_PERIODS, asset_page_chart, asset_page_deltas, fx_page_deltas
from backend.test_scripts.fixtures.period_changes.seeds import TERMINATING_PRICES, TERMINATING_RATES, last_on_or_before, scattered_days, series
from backend.test_scripts.test_utils import unique_id

# ============================================================================
# THE DATA: currencies, pairs and days of this file only
# ============================================================================

NATIVE = "AMD"  # the assets' own currency
TARGET = "BDT"  # AMD < BDT: stored AMD/BDT, a conversion to BDT multiplies
FOREIGN = "SZL"  # a price row in another currency; AMD/SZL has one rate, after every anchor of this file
PARTIAL = "LSL"  # an asset priced in LSL; AMD/LSL rates start inside the periods of one anchor
FX_PAIR = ("BBD", "BZD")  # the FX service's pair, rates on scattered days
EMPTY_PAIR = ("MVR", "SCR")  # never seeded
OWNED_PAIRS = ((NATIVE, TARGET), (NATIVE, FOREIGN), (NATIVE, PARTIAL), FX_PAIR, EMPTY_PAIR)
RATE_SOURCE = "MFP2-TEST"
PRICE_SOURCE = "mfp2_test"

THURSDAY = date(1987, 3, 12)
FRIDAY = date(1987, 3, 13)
SATURDAY = date(1987, 3, 14)
SUNDAY = date(1987, 3, 15)  # the weekend anchor: nothing stored on Saturday or Sunday
MONDAY = date(1987, 3, 16)
LAST_PRICE = date(1987, 6, 19)  # the six-year history's last row, a Friday
STALE = date(1987, 6, 30)  # the stale anchor, eleven days after it
HISTORY_FIRST = date(1981, 1, 2)
YOUNG_FIRST = SUNDAY - timedelta(days=200)  # younger than 1Y at SUNDAY, older than 6M
MIXED_FOREIGN_DAY = SUNDAY - timedelta(days=1100)  # the one SZL row of an AMD history: the price of both 2Y and 3Y
RATES_FIRST = date(1980, 12, 1)  # before every price: the target-currency series converts end to end
RATES_LAST = date(1987, 12, 31)
PARTIAL_RATES_FIRST = date(1987, 1, 1)
PARTIAL_AS_OF = date(1987, 4, 11)  # − 100 days = PARTIAL_RATES_FIRST: between 3M (91) and 6M (182)
UNCOVERED_AS_OF = date(1986, 12, 31)  # the day before the first AMD/LSL rate
FX_EDGE_AS_OF = RATES_FIRST + timedelta(days=1824)  # its 5Y reference is the day before the pair's first rate
FX_AS_OFS = (SUNDAY, MONDAY, date(1986, 7, 1), STALE, FX_EDGE_AS_OF)

#: The price query's range for the page: ``[as_of − 5Y − a bit, as_of]``.
PAGE_RANGE_DAYS = 1825 + 10
#: An asset id no row can carry.
UNKNOWN_ASSET_ID = 2**62 - 1

PRICE_GAPS = (3, 4, 11, 1, 6, 17, 2, 9, 5, 1)
RATE_GAPS = (4, 9, 1, 6, 12, 3)
FX_GAPS = (5, 8, 2, 13, 7, 3, 4)

SHORT_PERIODS = ("1D", "1W", "1M", "3M")
LONG_PERIODS = ("6M", "1Y", "2Y", "3Y", "5Y")
PERIOD_DAYS = dict(PAGE_PERIODS)
ALL_PERIODS = tuple(PERIOD_DAYS)


def _valued_days(as_of: date) -> list[date]:
    """``as_of`` and ``as_of − N`` for every period: the days a fixed-period table values."""
    return [as_of, *(as_of - timedelta(days=days) for _key, days in PAGE_PERIODS)]


def _sparse_prices() -> dict[date, Decimal]:
    """Six and a half years of irregular closes, with the rows the pins need."""
    days = [day for day in scattered_days(HISTORY_FIRST, LAST_PRICE, PRICE_GAPS) if day not in (SATURDAY, SUNDAY)]
    prices = series(days, TERMINATING_PRICES, 7)
    # The weekend: Thursday ≠ Friday, nothing on Saturday or Sunday. The 1M reference of SUNDAY exactly on a stored
    # row. The last row, LAST_PRICE, eleven days before STALE.
    prices.update({THURSDAY: Decimal("125"), FRIDAY: Decimal("160"), SUNDAY - timedelta(days=30): Decimal("64"), LAST_PRICE: Decimal("200")})
    return prices


def _target_rates() -> dict[date, Decimal]:
    """AMD/BDT from before the first price, on days of their own: the rate moves on days that have no price."""
    rates = series(scattered_days(RATES_FIRST, RATES_LAST, RATE_GAPS), TERMINATING_RATES, 3)
    rates.update({SATURDAY: Decimal("2"), SUNDAY: Decimal("2.5")})
    return rates


def _fx_rates() -> dict[date, Decimal]:
    """BBD/BZD on scattered days; one on SUNDAY − 30 (a reference on a stored rate), none on the weekend."""
    rates = series(scattered_days(RATES_FIRST, RATES_LAST, FX_GAPS), TERMINATING_RATES, 7)
    rates.pop(SATURDAY, None)
    rates.pop(SUNDAY, None)
    rates[SUNDAY - timedelta(days=30)] = Decimal("3.2")
    return rates


def _mixed_rows() -> list[tuple[date, Decimal, str]]:
    """An AMD history with one SZL row: the last price on or before both SUNDAY − 730 and SUNDAY − 1095."""
    early = scattered_days(SUNDAY - timedelta(days=2000), SUNDAY - timedelta(days=1101), (10,))
    late = scattered_days(SUNDAY - timedelta(days=700), SUNDAY - timedelta(days=2), (10,))
    rows = [(day, close, NATIVE) for day, close in series(early + late, TERMINATING_PRICES, 7).items()]
    return [*rows, (MIXED_FOREIGN_DAY, Decimal("100"), FOREIGN)]


def _switched_rows() -> list[tuple[date, Decimal, str]]:
    """An AMD history whose anchor, SUNDAY, is priced in SZL."""
    days = scattered_days(SUNDAY - timedelta(days=2000), SUNDAY - timedelta(days=3), (10,))
    return [*((day, close, NATIVE) for day, close in series(days, TERMINATING_PRICES, 5).items()), (SUNDAY, Decimal("80"), FOREIGN)]


# ============================================================================
# FIXTURE: seeded once for the module, removed at its end
# ============================================================================


@dataclass(frozen=True)
class _Seeded:
    assets: dict[str, int]
    sparse_prices: dict[date, Decimal]
    target_rates: dict[date, Decimal]
    fx_rates: dict[date, Decimal]


def _owned_pairs_clause():
    return or_(*(and_(FxRate.base == base, FxRate.quote == quote) for base, quote in OWNED_PAIRS))


async def _seed() -> _Seeded:
    stamp = f"{unique_id('MFP2')}-{uuid4().hex[:8]}"
    sparse_prices, target_rates, fx_rates = _sparse_prices(), _target_rates(), _fx_rates()
    rows_by_asset = {
        "sparse": [(day, close, NATIVE) for day, close in sparse_prices.items()],
        "young": [(day, close, NATIVE) for day, close in series(scattered_days(YOUNG_FIRST, FRIDAY, PRICE_GAPS), TERMINATING_PRICES, 5).items()],
        "mixed": _mixed_rows(),
        "switched": _switched_rows(),
        "partial": [(day, close, PARTIAL) for day, close in series(scattered_days(HISTORY_FIRST, LAST_PRICE, PRICE_GAPS), TERMINATING_PRICES, 7).items()],
    }
    rates_by_pair = {
        (NATIVE, TARGET): target_rates,
        (NATIVE, FOREIGN): {SUNDAY + timedelta(days=1): Decimal("2")},
        (NATIVE, PARTIAL): series(scattered_days(PARTIAL_RATES_FIRST, RATES_LAST, (10,)), TERMINATING_RATES, 3),
        FX_PAIR: fx_rates,
    }
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        await session.execute(delete(FxRate).where(_owned_pairs_clause()))
        assets = {name: Asset(display_name=f"MF-P2 {name} {stamp}", currency=PARTIAL if name == "partial" else NATIVE, asset_type=AssetType.STOCK, active=True) for name in rows_by_asset}
        session.add_all(assets.values())
        await session.flush()
        session.add_all(PriceHistory(asset_id=assets[name].id, date=day, close=close, currency=currency, source_plugin_key=PRICE_SOURCE) for name, rows in rows_by_asset.items() for day, close, currency in rows)
        session.add_all(FxRate(date=day, base=base, quote=quote, rate=rate, source=RATE_SOURCE) for (base, quote), rates in rates_by_pair.items() for day, rate in rates.items())
        await session.commit()
        return _Seeded(assets={name: asset.id for name, asset in assets.items()}, sparse_prices=sparse_prices, target_rates=target_rates, fx_rates=fx_rates)


async def _cleanup(asset_ids: Iterable[int]) -> None:
    ids = list(asset_ids)
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        await session.execute(delete(PriceHistory).where(PriceHistory.asset_id.in_(ids)))
        await session.execute(delete(Asset).where(Asset.id.in_(ids)))
        await session.execute(delete(FxRate).where(_owned_pairs_clause()))
        await session.commit()


@pytest.fixture(scope="module")
def seeded() -> Iterator[_Seeded]:
    data = asyncio.run(_seed())
    try:
        yield data
    finally:
        asyncio.run(_cleanup(data.assets.values()))


# ============================================================================
# HELPERS
# ============================================================================


async def _asset_changes(*items: FAPeriodChangesQueryItem) -> list[FAPeriodChangesResult]:
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        return await get_period_changes_bulk(list(items), session)


async def _fx_changes(*requests: FXPeriodChangesRequest) -> list[FXPeriodChangesResult]:
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        return await get_fx_period_changes_bulk(list(requests), session)


def _item(asset_id: int, as_of: date, target_currency: str | None = None) -> FAPeriodChangesQueryItem:
    return FAPeriodChangesQueryItem(asset_id=asset_id, as_of=as_of, target_currency=target_currency)


def _pair(base: str, quote: str, as_of: date) -> FXPeriodChangesRequest:
    return FXPeriodChangesRequest(base=base, quote=quote, as_of=as_of)


def _by_key(result: FAPeriodChangesResult) -> dict[str, Decimal | None]:
    return {period.key: period.change_ratio for period in result.periods}


def _percent(ratio: Decimal | None) -> Decimal | None:
    return None if ratio is None else ratio * 100


async def _price_query(asset_id: int, as_of: date, target_currency: str | None) -> FAPriceQueryResult:
    """``POST /assets/prices/query`` as the page asks it, through its service: the dense series up to ``as_of``."""
    item = FAPriceQueryItem(asset_id=asset_id, date_range=DateRangeModel(start=as_of - timedelta(days=PAGE_RANGE_DAYS), end=as_of), target_currency=target_currency)
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        [result] = await AssetSourceManager.get_prices_bulk([item], session)
    assert result.prices and result.prices[-1].date == as_of, f"the price query must reach {as_of}: {result.prices[-1:]}"
    return result


async def _asset_page(asset_id: int, as_of: date, target_currency: str | None, currency: str) -> dict[str, Decimal | None]:
    """The Δ columns the Assets page computes on that series — whose every point is in ``currency``, converted without
    error, or the comparison would be about a mixed series."""
    result = await _price_query(asset_id, as_of, target_currency)
    assert result.errors == [], f"the page's series must convert end to end: {result.errors}"
    assert {point.currency for point in result.prices} == {currency}
    return asset_page_deltas(asset_page_chart((point.date, point.close) for point in result.prices))


def _assert_matches_page(result: FAPeriodChangesResult, page: Mapping[str, Decimal | None], keys: Iterable[str] = ALL_PERIODS) -> None:
    """``change_ratio × 100`` equals the page's percentage on every period of ``keys``, None where the page has none."""
    wanted = set(keys)
    for period in result.periods:
        if period.key in wanted:
            assert _percent(period.change_ratio) == page[period.key], f"asset {result.asset_id} as of {result.as_of}, {period.key}: service {_percent(period.change_ratio)} %, page {page[period.key]} %"


async def _fx_page_data(base: str, quote: str, as_of: date) -> list[tuple[date, Decimal]]:
    """The FX page's points: ``POST /fx/currencies/convert`` of 1 base over the range answers each day its conversion
    succeeded, with ``rate = converted amount / 1`` — ``convert_bulk`` on every day, the service under that endpoint."""
    days = [as_of - timedelta(days=offset) for offset in range(PAGE_RANGE_DAYS, -1, -1)]
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        converted, _errors = await convert_bulk(session, [(Currency(code=base, amount=Decimal(1)), quote, day) for day in days], raise_on_error=False)
    return [(day, result[0].amount / Decimal(1)) for day, result in zip(days, converted, strict=True) if result is not None]


# ============================================================================
# WHAT X PINNED
# ============================================================================


@pytest.mark.asyncio
async def test_periods_are_the_page_columns_in_display_order(seeded):
    """Both answers list 1D … 5Y in the pages' display order, each with its ``days``: 1D included."""
    [asset] = await _asset_changes(_item(seeded.assets["sparse"], SUNDAY))
    [pair] = await _fx_changes(_pair(*FX_PAIR, SUNDAY))

    assert [(period.key, period.days) for period in asset.periods] == list(PAGE_PERIODS)
    assert [(period.key, period.days) for period in pair.periods] == list(PAGE_PERIODS)


@pytest.mark.asyncio
async def test_one_day_over_a_weekend_is_exactly_zero(seeded):
    """``as_of`` a Sunday: anchor and 1D reference are both Friday's carried price, a change of exactly 0, not None."""
    prices = seeded.sparse_prices
    assert SATURDAY not in prices and SUNDAY not in prices and prices[THURSDAY] != prices[FRIDAY], "precondition: Friday's price is the last before the weekend and differs from Thursday's"

    [result] = await _asset_changes(_item(seeded.assets["sparse"], SUNDAY))

    one_day = _by_key(result)["1D"]
    assert one_day is not None and one_day == 0, f"1D over the weekend: {one_day}"


# ============================================================================
# ASSETS — PARITY WITH THE PAGE
# ============================================================================


@pytest.mark.asyncio
async def test_six_year_history_matches_the_page_natively(seeded):
    """Sparse prices over six years: every period present at each anchor (a Sunday, a Monday, a priced Friday, a stale
    Tuesday), and each equal to the page's computePeriodDelta on the price query's series."""
    asset_id = seeded.assets["sparse"]
    results = await _asset_changes(*(_item(asset_id, as_of) for as_of in (SUNDAY, MONDAY, FRIDAY, STALE)))

    for result in results:
        assert result.currency == NATIVE and result.errors == []
        assert all(period.change_ratio is not None for period in result.periods), f"as of {result.as_of}: {_by_key(result)}"
        _assert_matches_page(result, await _asset_page(asset_id, result.as_of, None, NATIVE))


@pytest.mark.asyncio
async def test_six_year_history_matches_the_page_in_a_target_currency(seeded):
    """Converted, each day at its own rate — rates that also move on days without a price — the changes are still the
    page's; and over the weekend the 1D is the rate's move alone, Saturday's rate to Sunday's on Friday's price."""
    asset_id = seeded.assets["sparse"]
    results = await _asset_changes(*(_item(asset_id, as_of, TARGET) for as_of in (SUNDAY, MONDAY, FRIDAY, STALE)))

    for result in results:
        assert result.currency == TARGET and result.errors == []
        assert all(period.change_ratio is not None for period in result.periods), f"as of {result.as_of}: {_by_key(result)}"
        _assert_matches_page(result, await _asset_page(asset_id, result.as_of, TARGET, TARGET))
    rates = seeded.target_rates
    assert _by_key(results[0])["1D"] == rates[SUNDAY] / rates[SATURDAY] - 1 == Decimal("0.25")


@pytest.mark.asyncio
async def test_asset_younger_than_a_year_has_only_the_short_periods(seeded):
    """First price 200 days before ``as_of``: 1D … 6M present, 1Y … 5Y None — natively and converted, as on the page."""
    asset_id = seeded.assets["young"]

    for target, currency in ((None, NATIVE), (TARGET, TARGET)):
        [result] = await _asset_changes(_item(asset_id, SUNDAY, target))
        changes = _by_key(result)
        assert [key for key, change in changes.items() if change is not None] == ["1D", "1W", "1M", "3M", "6M"], changes
        _assert_matches_page(result, await _asset_page(asset_id, SUNDAY, target, currency))


@pytest.mark.asyncio
async def test_stale_anchor_is_the_last_price_before_as_of(seeded):
    """Last price eleven days before ``as_of``: it is the anchor of every period, so 1D and 1W are exactly 0 and the
    others compare it with the last price on or before ``as_of − N``."""
    prices = seeded.sparse_prices
    anchor = last_on_or_before(prices, STALE)
    assert anchor == prices[LAST_PRICE] and max(prices) == LAST_PRICE, "precondition: nothing stored after LAST_PRICE"

    [result] = await _asset_changes(_item(seeded.assets["sparse"], STALE))

    for period in result.periods:
        assert period.change_ratio == anchor / last_on_or_before(prices, STALE - timedelta(days=period.days)) - 1, period.key
    assert _by_key(result)["1D"] == 0 and _by_key(result)["1W"] == 0


# ============================================================================
# ASSETS — BULK SHAPE
# ============================================================================


@pytest.mark.asyncio
async def test_bulk_answers_in_request_order_each_at_its_own_as_of(seeded):
    """Two assets in one call, one of them twice with different ``as_of``: the answer keeps the request order, and each
    item is what it would be alone."""
    young, sparse = seeded.assets["young"], seeded.assets["sparse"]
    items = [_item(young, SUNDAY), _item(sparse, STALE, TARGET), _item(young, SUNDAY - timedelta(days=40)), _item(sparse, SUNDAY)]

    batch = await _asset_changes(*items)

    assert [(result.asset_id, result.as_of) for result in batch] == [(item.asset_id, item.as_of) for item in items]
    for item, result in zip(items, batch, strict=True):
        assert [result] == await _asset_changes(item)
    # The same asset at two anchors: 200 days of history cover 6M at SUNDAY, not at SUNDAY − 40.
    assert _by_key(batch[0])["6M"] is not None and _by_key(batch[2])["6M"] is None


@pytest.mark.asyncio
async def test_unknown_asset_has_no_change_no_currency_no_errors(seeded):
    """An id without a price: every change None, no currency natively, and no error at all — nor in its neighbour."""
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        stored = (await session.execute(select(func.count()).select_from(PriceHistory).where(PriceHistory.asset_id == UNKNOWN_ASSET_ID))).scalar_one()
    assert stored == 0, "precondition: no price row carries UNKNOWN_ASSET_ID"

    unknown, known = await _asset_changes(_item(UNKNOWN_ASSET_ID, SUNDAY), _item(seeded.assets["sparse"], SUNDAY))
    [converted] = await _asset_changes(_item(UNKNOWN_ASSET_ID, SUNDAY, TARGET))

    assert unknown.asset_id == UNKNOWN_ASSET_ID and unknown.currency is None and unknown.errors == []
    assert all(change is None for change in _by_key(unknown).values())
    assert converted.errors == [] and all(change is None for change in _by_key(converted).values())
    assert [known] == await _asset_changes(_item(seeded.assets["sparse"], SUNDAY))


# ============================================================================
# ASSETS — CURRENCIES
# ============================================================================


@pytest.mark.asyncio
async def test_native_mode_leaves_out_a_price_in_another_currency(seeded):
    """Natively the anchor's currency rules: the SZL row that prices both 2Y and 3Y gives those two None and one
    error, once; every other period is computed."""
    [result] = await _asset_changes(_item(seeded.assets["mixed"], SUNDAY))

    changes = _by_key(result)
    assert result.currency == NATIVE
    assert [key for key, change in changes.items() if change is None] == ["2Y", "3Y"], changes
    assert result.errors == [f"Price of {MIXED_FOREIGN_DAY} is in {FOREIGN}, not {NATIVE}"]


@pytest.mark.asyncio
async def test_target_currency_without_a_rate_on_the_anchor_day(seeded):
    """With unlimited backward fill a rate is missing on a day only before the pair's first rate. The anchor, priced in
    SZL, needs SZL → AMD, and the only AMD/SZL rate is dated the day after: every change None, and one error."""
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        first_rate = (await session.execute(select(func.min(FxRate.date)).where(FxRate.base == NATIVE, FxRate.quote == FOREIGN))).scalar_one()
    assert first_rate == SUNDAY + timedelta(days=1), "precondition: AMD/SZL starts after the anchor"

    [result] = await _asset_changes(_item(seeded.assets["switched"], SUNDAY, NATIVE))

    assert result.currency == NATIVE
    assert all(change is None for change in _by_key(result).values()), _by_key(result)
    assert result.errors == [f"No {FOREIGN}/{NATIVE} rate on or before {SUNDAY}"]


@pytest.mark.asyncio
async def test_target_currency_rates_starting_inside_the_periods(seeded):
    """AMD/LSL starts 100 days before ``as_of``: 1D … 3M convert and equal the page's, 6M … 5Y are None, one error for
    each of their days."""
    asset_id = seeded.assets["partial"]

    [result] = await _asset_changes(_item(asset_id, PARTIAL_AS_OF, NATIVE))

    changes = _by_key(result)
    assert result.currency == NATIVE
    assert [key for key, change in changes.items() if change is not None] == list(SHORT_PERIODS), changes
    assert sorted(result.errors) == sorted(f"No {PARTIAL}/{NATIVE} rate on or before {PARTIAL_AS_OF - timedelta(days=PERIOD_DAYS[key])}" for key in LONG_PERIODS)
    # The page's series also holds the unconverted LSL closes before the first rate: compare only what it converted.
    page_series = await _price_query(asset_id, PARTIAL_AS_OF, NATIVE)
    _assert_matches_page(result, asset_page_deltas(asset_page_chart((point.date, point.close) for point in page_series.prices)), SHORT_PERIODS)


@pytest.mark.asyncio
async def test_target_currency_without_any_rate_up_to_as_of(seeded):
    """No AMD/LSL rate on or before ``as_of``: every change None, one error per valued day — ten, unique, within the
    cap of ten (no «… and N more»)."""
    [result] = await _asset_changes(_item(seeded.assets["partial"], UNCOVERED_AS_OF, NATIVE))

    assert result.currency == NATIVE
    assert all(change is None for change in _by_key(result).values())
    assert len(result.errors) == len(set(result.errors)) == 10
    assert set(result.errors) == {f"No {PARTIAL}/{NATIVE} rate on or before {day}" for day in _valued_days(UNCOVERED_AS_OF)}


# ============================================================================
# FX
# ============================================================================


@pytest.mark.asyncio
async def test_fx_changes_are_the_seeded_rates_both_ways(seeded):
    """``change_ratio = rate(as_of) / rate(as_of − N) − 1`` and ``inverse_change_ratio = rate(as_of − N) / rate(as_of)
    − 1``, each rate the last seeded on or before its day; the 5Y of FX_EDGE_AS_OF has no rate (covered below)."""
    rates = seeded.fx_rates
    results = await _fx_changes(*(_pair(*FX_PAIR, as_of) for as_of in FX_AS_OFS if as_of != FX_EDGE_AS_OF))

    for result in results:
        anchor = last_on_or_before(rates, result.as_of)
        assert result.errors == [], result.errors
        for period in result.periods:
            reference = last_on_or_before(rates, result.as_of - timedelta(days=period.days))
            assert period.change_ratio == anchor / reference - 1, f"{result.as_of} {period.key}"
            assert period.inverse_change_ratio == reference / anchor - 1, f"{result.as_of} {period.key}"


@pytest.mark.asyncio
async def test_fx_changes_match_the_page_on_daily_conversions(seeded):
    """The FX page's computePeriodDelta on the per-day conversions of the range, both orientations: the same numbers."""
    for as_of in FX_AS_OFS:
        [result] = await _fx_changes(_pair(*FX_PAIR, as_of))
        data = await _fx_page_data(*FX_PAIR, as_of)
        direct, inverse = fx_page_deltas(data, inverted=False), fx_page_deltas(data, inverted=True)

        for period in result.periods:
            assert _percent(period.change_ratio) == direct[period.key], f"{as_of} {period.key}"
            assert _percent(period.inverse_change_ratio) == inverse[period.key], f"{as_of} {period.key} inverted"


@pytest.mark.asyncio
async def test_fx_reversed_pair_swaps_the_orientations(seeded):
    """Asked quote → base, the pair's change is the other's inverse change, and the other way round."""
    forward, backward = await _fx_changes(_pair(*FX_PAIR, SUNDAY), _pair(FX_PAIR[1], FX_PAIR[0], SUNDAY))

    assert (backward.base, backward.quote) == (FX_PAIR[1], FX_PAIR[0])
    for ahead, back in zip(forward.periods, backward.periods, strict=True):
        assert ahead.change_ratio is not None and back.change_ratio is not None
        assert (back.change_ratio, back.inverse_change_ratio) == (ahead.inverse_change_ratio, ahead.change_ratio), ahead.key


@pytest.mark.asyncio
async def test_fx_pair_without_rates(seeded):
    """A pair with no rate at all: every change None in both orientations, one error naming the pair per valued day."""
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        stored = (await session.execute(select(func.count()).select_from(FxRate).where(FxRate.base == EMPTY_PAIR[0], FxRate.quote == EMPTY_PAIR[1]))).scalar_one()
    assert stored == 0, "precondition: MVR/SCR has no rate"

    [result] = await _fx_changes(_pair(*EMPTY_PAIR, SUNDAY))

    assert all(period.change_ratio is None and period.inverse_change_ratio is None for period in result.periods)
    assert sorted(result.errors) == sorted(f"No {EMPTY_PAIR[0]}/{EMPTY_PAIR[1]} rate on or before {day}" for day in _valued_days(SUNDAY))


@pytest.mark.asyncio
async def test_fx_reference_before_the_first_rate(seeded):
    """The 5Y reference falls the day before the pair's first rate: 5Y None both ways, one error; the rest computed."""
    assert min(seeded.fx_rates) == RATES_FIRST, "precondition: BBD/BZD starts on RATES_FIRST"

    [result] = await _fx_changes(_pair(*FX_PAIR, FX_EDGE_AS_OF))

    assert [period.key for period in result.periods if period.change_ratio is None] == ["5Y"]
    assert [period.key for period in result.periods if period.inverse_change_ratio is None] == ["5Y"]
    assert result.errors == [f"No {FX_PAIR[0]}/{FX_PAIR[1]} rate on or before {RATES_FIRST - timedelta(days=1)}"]


@pytest.mark.asyncio
async def test_fx_bulk_answers_in_request_order(seeded):
    """Pairs in one call, one of them reversed and one without rates: the request order, each item as it is alone."""
    requests = [_pair(*FX_PAIR, SUNDAY), _pair(*EMPTY_PAIR, MONDAY), _pair(FX_PAIR[1], FX_PAIR[0], STALE)]

    batch = await _fx_changes(*requests)

    assert [(result.base, result.quote, result.as_of) for result in batch] == [(request.base, request.quote, request.as_of) for request in requests]
    for request, result in zip(requests, batch, strict=True):
        assert [result] == await _fx_changes(request)


@pytest.mark.parametrize(("base", "quote"), [("BBD", "BBD"), ("bbd", "BBD")])
def test_fx_request_refuses_one_currency_on_both_sides(base, quote):
    """base == quote — after the codes are normalised — is refused by the schema (a 422 at the route)."""
    with pytest.raises(ValidationError, match="base and quote must differ"):
        FXPeriodChangesRequest(base=base, quote=quote, as_of=SUNDAY)
