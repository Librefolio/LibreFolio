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

X-R59 (rule 10, decision N80) — the whole-range change, ``TestAssetRangeChange`` and ``TestFxRangeChange`` at the end.
An item may ask ``range_start``; its result then carries ``range_change``: ``reference_date``, ``change_abs``,
``change_ratio`` (+ ``inverse_change_abs``, ``inverse_change_ratio`` for FX), what the Assets cards and the FX Δ Abs / Δ %
compute in the browser today from the first and last point of the loaded series. The reference is the value on
``range_start`` (the last one on or before it; ``reference_date`` is ``range_start`` itself), else the first value in
``(range_start, as_of]`` (``reference_date`` its date), else none (``reference_date`` null); the anchor is the value on
``as_of``, as for the periods; with a target currency the reference is converted at ``reference_date``'s rate. They use
the same seeded rows as the periods — no new data. RED on HEAD (a275ec8af, 46bbbb1e3): the items refuse ``range_start``
(``extra_forbidden``) and the results have no ``range_change``; ``test_range_change_is_null_without_range_start`` is the
one guard, green before and after.

``TestLiveRangeChange`` — the asset page's live quote (X-R59, decision c): ``live_range_changes(session, results,
range_start)``, behind ``POST /assets/prices/current?range_start=…``, gives each current price its whole-range change.
The anchor is the result's own ``value`` in its ``currency`` — a live quote that may not be stored —, the reference the
period changes' rule up to the result's ``as_of_date``. The tests hand it ``FACurrentPriceItem``s built here (no provider)
on the seeded histories. RED on HEAD 46bbbb1e3: the function does not exist (looked up on the module when called).
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
from backend.app.schemas.prices import FACurrentPriceItem, FAPeriodChangesQueryItem, FAPeriodChangesResult, FAPriceQueryItem, FAPriceQueryResult
from backend.app.services.assets import period_changes as asset_period_changes
from backend.app.services.assets.manager import AssetSourceManager
from backend.app.services.assets.period_changes import get_period_changes_bulk
from backend.app.services.financial_math import returns as returns_module
from backend.app.services.fx.conversion import convert_bulk
from backend.app.services.fx.period_changes import get_fx_period_changes_bulk
from backend.test_scripts.fixtures.period_changes.page_ports import PAGE_PERIODS, asset_page_chart, asset_page_deltas, fx_page_deltas
from backend.test_scripts.fixtures.period_changes.seeds import TERMINATING_PRICES, TERMINATING_RATES, first_carried_day, last_on_or_before, scattered_days, series
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


def _young_prices() -> dict[date, Decimal]:
    """An AMD history that starts 200 days before SUNDAY and ends on FRIDAY."""
    return series(scattered_days(YOUNG_FIRST, FRIDAY, PRICE_GAPS), TERMINATING_PRICES, 5)


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
    young_prices: dict[date, Decimal]
    target_rates: dict[date, Decimal]
    fx_rates: dict[date, Decimal]


def _owned_pairs_clause():
    return or_(*(and_(FxRate.base == base, FxRate.quote == quote) for base, quote in OWNED_PAIRS))


async def _seed() -> _Seeded:
    stamp = f"{unique_id('MFP2')}-{uuid4().hex[:8]}"
    sparse_prices, young_prices, target_rates, fx_rates = _sparse_prices(), _young_prices(), _target_rates(), _fx_rates()
    rows_by_asset = {
        "sparse": [(day, close, NATIVE) for day, close in sparse_prices.items()],
        "young": [(day, close, NATIVE) for day, close in young_prices.items()],
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
        return _Seeded(assets={name: asset.id for name, asset in assets.items()}, sparse_prices=sparse_prices, young_prices=young_prices, target_rates=target_rates, fx_rates=fx_rates)


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


def _item(asset_id: int, as_of: date, target_currency: str | None = None, range_start: date | None = None) -> FAPeriodChangesQueryItem:
    """An asset item; ``range_start`` is passed only when given, so an item without it is valid on HEAD too."""
    return FAPeriodChangesQueryItem(asset_id=asset_id, as_of=as_of, target_currency=target_currency, **({} if range_start is None else {"range_start": range_start}))


def _pair(base: str, quote: str, as_of: date, range_start: date | None = None) -> FXPeriodChangesRequest:
    return FXPeriodChangesRequest(base=base, quote=quote, as_of=as_of, **({} if range_start is None else {"range_start": range_start}))


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


# ============================================================================
# X-R59 — THE WHOLE-RANGE CHANGE (rule 10, decision N80)
# ============================================================================

#: The mixed asset's anchor for its range test. Every period of it reads an AMD row — the last row, SUNDAY − 10, for 1D
#: … 1Y, then SUNDAY − 330, SUNDAY − 700 and SUNDAY − 1430 —, so the only foreign price the item meets is the range's.
MIXED_RANGE_AS_OF = SUNDAY + timedelta(days=400)
#: Its range start: the last price on or before it is the SZL row (MIXED_FOREIGN_DAY, SUNDAY − 1100).
MIXED_RANGE_START = SUNDAY - timedelta(days=800)
#: The young asset's range start: 50 days before its first price, so its history starts inside the range.
YOUNG_RANGE_START = YOUNG_FIRST - timedelta(days=50)


def _range(result: FAPeriodChangesResult | FXPeriodChangesResult):
    """The result's ``range_change``: an item that asked ``range_start`` always has one, an object, even when empty."""
    assert result.range_change is not None, f"an item with range_start answers a range_change object: {result}"
    return result.range_change


async def _price_row_count(asset_id: int) -> int:
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        return (await session.execute(select(func.count()).select_from(PriceHistory).where(PriceHistory.asset_id == asset_id))).scalar_one()


@pytest.mark.asyncio
class TestAssetRangeChange:
    """``range_change`` of an asset item: ``reference_date``, ``change_abs``, ``change_ratio``. RED on HEAD a275ec8af
    (the item refuses ``range_start``) except the first test, a guard."""

    async def test_range_change_is_null_without_range_start(self, seeded):
        """Guard, green on HEAD too: an item without ``range_start`` asks no range change — native, converted, unknown."""
        results = await _asset_changes(_item(seeded.assets["sparse"], SUNDAY), _item(seeded.assets["sparse"], STALE, TARGET), _item(UNKNOWN_ASSET_ID, SUNDAY))

        assert [getattr(result, "range_change", None) for result in results] == [None, None, None]

    async def test_range_start_leaves_the_periods_unchanged(self, seeded):
        """The same item with and without ``range_start``: the same currency, periods and errors — the range adds its
        ``range_change`` and nothing else, here on a reference with nothing wrong with it."""
        asset_id = seeded.assets["sparse"]
        for target in (None, TARGET):
            without, with_range = await _asset_changes(_item(asset_id, STALE, target), _item(asset_id, STALE, target, range_start=SATURDAY))

            assert (with_range.asset_id, with_range.as_of, with_range.currency, with_range.periods, with_range.errors) == (without.asset_id, without.as_of, without.currency, without.periods, without.errors), target
            assert without.range_change is None and with_range.range_change is not None, target

    async def test_reference_carried_from_before_range_start(self, seeded):
        """Nothing stored on SATURDAY: the reference is Friday's 160 carried, the day reported SATURDAY itself — as the
        price query's first point —, and the anchor the last price on or before STALE, 200."""
        prices = seeded.sparse_prices
        assert SATURDAY not in prices and last_on_or_before(prices, SATURDAY) == prices[FRIDAY] == Decimal("160"), "precondition: SATURDAY carries Friday's price"
        assert last_on_or_before(prices, STALE) == prices[LAST_PRICE] == Decimal("200"), "precondition: STALE carries LAST_PRICE"

        [result] = await _asset_changes(_item(seeded.assets["sparse"], STALE, range_start=SATURDAY))

        change = _range(result)
        assert result.currency == NATIVE and result.errors == []
        assert change.reference_date == SATURDAY
        assert change.change_abs == Decimal("40")
        assert change.change_ratio == Decimal("0.25")

    async def test_history_starting_inside_the_range(self, seeded):
        """First price 50 days after ``range_start``: the reference is that first price, ``reference_date`` its date."""
        prices = seeded.young_prices
        anchor = last_on_or_before(prices, SUNDAY)
        assert min(prices) == YOUNG_FIRST > YOUNG_RANGE_START, "precondition: the history starts inside the range"
        assert prices[YOUNG_FIRST] != anchor, "precondition: the range has a move"

        [result] = await _asset_changes(_item(seeded.assets["young"], SUNDAY, range_start=YOUNG_RANGE_START))

        change = _range(result)
        assert change.reference_date == YOUNG_FIRST
        assert change.change_abs == anchor - prices[YOUNG_FIRST]
        assert change.change_ratio == anchor / prices[YOUNG_FIRST] - 1

    async def test_no_price_up_to_as_of(self, seeded):
        """No price on or before ``as_of`` — prices only after it, or none at all: ``reference_date`` and both changes
        null, natively and in a target currency."""
        young_as_of = YOUNG_FIRST - timedelta(days=1)
        assert min(seeded.young_prices) > young_as_of, "precondition: the young asset is priced only after its as_of"
        assert await _price_row_count(UNKNOWN_ASSET_ID) == 0, "precondition: no price row carries UNKNOWN_ASSET_ID"
        items = [
            _item(seeded.assets["young"], young_as_of, range_start=young_as_of - timedelta(days=30)),
            _item(seeded.assets["young"], young_as_of, TARGET, range_start=young_as_of - timedelta(days=30)),
            _item(UNKNOWN_ASSET_ID, SUNDAY, range_start=SATURDAY),
            _item(UNKNOWN_ASSET_ID, SUNDAY, TARGET, range_start=SATURDAY),
        ]

        results = await _asset_changes(*items)

        for item, result in zip(items, results, strict=True):
            change = _range(result)
            assert (change.reference_date, change.change_abs, change.change_ratio) == (None, None, None), (item, change)

    async def test_native_reference_in_another_currency(self, seeded):
        """Natively the anchor's currency rules, as for the periods: the reference on MIXED_RANGE_START is the SZL row,
        so both changes are null and one error line names that row. Every period of the item reads an AMD row and is
        valued, so the line is the range's."""
        [result] = await _asset_changes(_item(seeded.assets["mixed"], MIXED_RANGE_AS_OF, range_start=MIXED_RANGE_START))

        change = _range(result)
        assert result.currency == NATIVE
        assert all(period.change_ratio is not None for period in result.periods), f"precondition: no period meets the SZL row: {_by_key(result)}"
        assert change.reference_date == MIXED_RANGE_START, "a price exists on or before range_start: the day reported is range_start"
        assert (change.change_abs, change.change_ratio) == (None, None)
        assert len(result.errors) == 1 and MIXED_FOREIGN_DAY.isoformat() in result.errors[0] and FOREIGN in result.errors[0], result.errors

    async def test_target_currency_converts_the_reference_at_reference_date(self, seeded):
        """In BDT the reference is converted at ``reference_date``'s rate. Carried: Friday's 160 AMD at SATURDAY's rate 2
        — not Friday's —, 320, against 160 at SUNDAY's 2.5, 400. Inside the range: the first price at its own day's rate."""
        prices, young, rates = seeded.sparse_prices, seeded.young_prices, seeded.target_rates
        assert last_on_or_before(rates, FRIDAY) != rates[SATURDAY], "precondition: the rate moves between the price's day and range_start"
        young_reference = young[YOUNG_FIRST] * last_on_or_before(rates, YOUNG_FIRST)
        young_anchor = last_on_or_before(young, SUNDAY) * rates[SUNDAY]

        carried, inside = await _asset_changes(_item(seeded.assets["sparse"], SUNDAY, TARGET, range_start=SATURDAY), _item(seeded.assets["young"], SUNDAY, TARGET, range_start=YOUNG_RANGE_START))

        assert carried.currency == inside.currency == TARGET and carried.errors == inside.errors == []
        change = _range(carried)
        assert change.reference_date == SATURDAY
        assert change.change_abs == prices[FRIDAY] * rates[SUNDAY] - prices[FRIDAY] * rates[SATURDAY] == Decimal("80")
        assert change.change_ratio == Decimal("0.25")
        change = _range(inside)
        assert change.reference_date == YOUNG_FIRST
        assert change.change_abs == young_anchor - young_reference
        assert change.change_ratio == young_anchor / young_reference - 1

    async def test_range_start_equal_to_as_of_is_zero(self, seeded):
        """A one-day range: the reference is the anchor, a change of exactly 0 — on a carried day, a priced one, converted."""
        asset_id = seeded.assets["sparse"]
        assert SUNDAY not in seeded.sparse_prices and FRIDAY in seeded.sparse_prices, "precondition: one carried day, one priced"
        items = [_item(asset_id, SUNDAY, range_start=SUNDAY), _item(asset_id, FRIDAY, range_start=FRIDAY), _item(asset_id, SUNDAY, TARGET, range_start=SUNDAY)]

        results = await _asset_changes(*items)

        for item, result in zip(items, results, strict=True):
            change = _range(result)
            assert change.reference_date == item.as_of, item
            assert change.change_abs == 0 and change.change_ratio == 0, (item, change)

    @pytest.mark.parametrize(
        ("name", "as_of", "range_start", "target"),
        [
            pytest.param("sparse", STALE, SATURDAY, None, id="carried"),
            pytest.param("sparse", SUNDAY, SATURDAY, TARGET, id="carried-converted"),
            pytest.param("young", SUNDAY, YOUNG_RANGE_START, None, id="inside"),
            pytest.param("young", SUNDAY, YOUNG_RANGE_START, TARGET, id="inside-converted"),
            pytest.param("sparse", SUNDAY, SUNDAY, None, id="one-day"),
        ],
    )
    async def test_range_change_is_the_price_query_first_and_last_point(self, seeded, name, as_of, range_start, target):
        """One home: the change equals what the Assets cards compute today from the first and last point of
        ``POST /assets/prices/query``'s series over ``[range_start, as_of]`` (its service, ``get_prices_bulk``)."""
        asset_id = seeded.assets[name]
        query = FAPriceQueryItem(asset_id=asset_id, date_range=DateRangeModel(start=range_start, end=as_of), target_currency=target)
        async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
            [series_result] = await AssetSourceManager.get_prices_bulk([query], session)
        points = series_result.prices
        assert series_result.errors == [] and points and points[-1].date == as_of, f"the series must convert and reach {as_of}: {series_result.errors} {points[-1:]}"
        first, last = points[0], points[-1]

        [result] = await _asset_changes(_item(asset_id, as_of, target, range_start=range_start))

        change = _range(result)
        assert change.reference_date == first.date
        assert change.change_abs == last.close - first.close, f"{change.change_abs} vs {last.close} − {first.close}"
        assert change.change_ratio == last.close / first.close - 1, f"{change.change_ratio} vs {last.close} / {first.close} − 1"


@pytest.mark.asyncio
class TestFxRangeChange:
    """``range_change`` of a pair: ``reference_date`` and the change in both orientations. RED on HEAD a275ec8af (the
    request refuses ``range_start``) except the first test, a guard."""

    async def test_range_change_is_null_without_range_start(self, seeded):
        """Guard, green on HEAD too: a request without ``range_start`` asks no range change — with rates or without."""
        results = await _fx_changes(_pair(*FX_PAIR, SUNDAY), _pair(FX_PAIR[1], FX_PAIR[0], STALE), _pair(*EMPTY_PAIR, SUNDAY))

        assert [getattr(result, "range_change", None) for result in results] == [None, None, None]

    async def test_range_start_leaves_the_periods_unchanged(self, seeded):
        range_start = first_carried_day(seeded.fx_rates, SUNDAY - timedelta(days=120), SUNDAY)

        without, with_range = await _fx_changes(_pair(*FX_PAIR, SUNDAY), _pair(*FX_PAIR, SUNDAY, range_start))

        assert (with_range.base, with_range.quote, with_range.as_of, with_range.periods, with_range.errors) == (without.base, without.quote, without.as_of, without.periods, without.errors)
        assert without.range_change is None and with_range.range_change is not None

    async def test_reference_carried_from_before_range_start(self, seeded):
        """No rate stored on ``range_start``: the reference is the last rate before it, the day reported ``range_start``;
        the change in both orientations, the inverse one of the pair read base per quote (``1 / rate``)."""
        rates = seeded.fx_rates
        range_start = first_carried_day(rates, SUNDAY - timedelta(days=120), SUNDAY)
        reference, anchor = last_on_or_before(rates, range_start), last_on_or_before(rates, SUNDAY)

        [result] = await _fx_changes(_pair(*FX_PAIR, SUNDAY, range_start))

        change = _range(result)
        assert change.reference_date == range_start
        assert change.change_abs == anchor - reference
        assert change.change_ratio == anchor / reference - 1
        assert change.inverse_change_abs == 1 / anchor - 1 / reference
        assert change.inverse_change_ratio == reference / anchor - 1

    async def test_rates_starting_inside_the_range(self, seeded):
        """The pair's first rate is 20 days after ``range_start``: the reference is that rate, ``reference_date`` its day
        — the first point ``POST /fx/currencies/convert`` answers for the range."""
        rates = seeded.fx_rates
        as_of, range_start = RATES_FIRST + timedelta(days=100), RATES_FIRST - timedelta(days=20)
        reference, anchor = rates[RATES_FIRST], last_on_or_before(rates, as_of)
        assert min(rates) == RATES_FIRST and reference != anchor, "precondition: BBD/BZD starts on RATES_FIRST and moves by as_of"

        [result] = await _fx_changes(_pair(*FX_PAIR, as_of, range_start))

        change = _range(result)
        assert change.reference_date == RATES_FIRST
        assert change.change_abs == anchor - reference
        assert change.change_ratio == anchor / reference - 1
        assert change.inverse_change_abs == 1 / anchor - 1 / reference
        assert change.inverse_change_ratio == reference / anchor - 1

    async def test_no_rate_up_to_as_of(self, seeded):
        """No rate on or before ``as_of`` — the pair starts after it, or has none: ``reference_date`` and all four null."""
        assert min(seeded.fx_rates) == RATES_FIRST, "precondition: BBD/BZD starts on RATES_FIRST"
        early_as_of = RATES_FIRST - timedelta(days=1)

        results = await _fx_changes(_pair(*FX_PAIR, early_as_of, early_as_of - timedelta(days=30)), _pair(*EMPTY_PAIR, SUNDAY, SATURDAY))

        for result in results:
            change = _range(result)
            values = (change.reference_date, change.change_abs, change.change_ratio, change.inverse_change_abs, change.inverse_change_ratio)
            assert values == (None, None, None, None, None), (result.base, result.quote, values)

    async def test_inverted_display_swaps_the_orientations(self, seeded):
        """The pair asked quote → base — the FX page's inverted display: its change, absolute and relative, is the
        other's inverse change, and the other way round."""
        range_start = first_carried_day(seeded.fx_rates, SUNDAY - timedelta(days=120), SUNDAY)

        forward, backward = await _fx_changes(_pair(*FX_PAIR, SUNDAY, range_start), _pair(FX_PAIR[1], FX_PAIR[0], SUNDAY, range_start))

        ahead, back = _range(forward), _range(backward)
        assert ahead.reference_date == back.reference_date == range_start
        assert ahead.change_abs is not None and ahead.inverse_change_abs is not None
        assert (back.change_abs, back.change_ratio) == (ahead.inverse_change_abs, ahead.inverse_change_ratio)
        assert (back.inverse_change_abs, back.inverse_change_ratio) == (ahead.change_abs, ahead.change_ratio)

    async def test_range_start_equal_to_as_of_is_zero(self, seeded):
        """A one-day range, on a day carried over the weekend and on a stale one: all four exactly 0."""
        assert SUNDAY not in seeded.fx_rates, "precondition: SUNDAY carries Friday's rate"

        results = await _fx_changes(_pair(*FX_PAIR, SUNDAY, SUNDAY), _pair(*FX_PAIR, STALE, STALE))

        for result in results:
            change = _range(result)
            assert change.reference_date == result.as_of
            assert change.change_abs == change.change_ratio == change.inverse_change_abs == change.inverse_change_ratio == 0, change


# ============================================================================
# X-R59 — THE LIVE QUOTE'S RANGE CHANGE (decision c, POST /prices/current?range_start=…)
# ============================================================================

#: A live quote: a value no seeded row has, in the assets' currency.
LIVE_VALUE = Decimal("250")
NO_CHANGE = (None, None, None)


def _live(asset_id: int, as_of_date: date | None = SUNDAY, value: Decimal | None = LIVE_VALUE, currency: str | None = NATIVE) -> FACurrentPriceItem:
    """A current price as ``POST /prices/current`` returns it from a provider: built here, never fetched nor stored."""
    return FACurrentPriceItem(asset_id=asset_id, value=value, currency=currency, as_of_date=as_of_date, source="provider:x-r59-test")


async def _live_changes(range_start: date, *items: FACurrentPriceItem) -> list[tuple[date | None, Decimal | None, Decimal | None]]:
    """``live_range_changes`` on ``items``, as ``(reference_date, change_abs, change_ratio)`` per item, in item order.

    The function is looked up on the module when called: it does not exist on HEAD 46bbbb1e3. The brief fixes what each
    result gets, not the container: a mapping by asset id (an asset it leaves out has no change — the route then fills an
    empty ``FARangeChange``) or a sequence in item order.
    """
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        changes = await asset_period_changes.live_range_changes(session, list(items), range_start)
    per_item = [changes.get(item.asset_id) for item in items] if isinstance(changes, Mapping) else list(changes)
    assert len(per_item) == len(items), f"one change per result: {changes}"
    return [NO_CHANGE if change is None else (change.reference_date, change.change_abs, change.change_ratio) for change in per_item]


def _house(reference: Decimal, anchor: Decimal) -> tuple[Decimal | None, Decimal | None]:
    """The house's ``range_change(reference, anchor)``: its two direct fields."""
    change = returns_module.range_change(reference, anchor)
    return change.change_abs, change.change_ratio


@pytest.mark.asyncio
class TestLiveRangeChange:
    """``live_range_changes(session, results, range_start)``: the change from the period changes' reference to each
    result's own price. RED on HEAD 46bbbb1e3: AttributeError, the function does not exist."""

    async def test_reference_carried_from_before_range_start(self, seeded):
        """Nothing stored on SATURDAY: the reference is Friday's 160 carried, ``reference_date`` SATURDAY; the anchor the
        live 250 of SUNDAY — a day nothing is stored on either."""
        prices = seeded.sparse_prices
        assert SATURDAY not in prices and SUNDAY not in prices and last_on_or_before(prices, SATURDAY) == prices[FRIDAY] == Decimal("160"), "precondition: SATURDAY carries Friday's price"

        [change] = await _live_changes(SATURDAY, _live(seeded.assets["sparse"]))

        assert change == (SATURDAY, Decimal("90"), Decimal("0.5625"))
        assert change[1:] == _house(prices[FRIDAY], LIVE_VALUE)

    async def test_anchor_is_the_live_value_not_the_stored_price(self, seeded):
        """A live quote on a day that has a stored price — FRIDAY, 160 —: the anchor is the quote, 250. From THURSDAY's
        125 that is +125, +100 %; the stored price would give +35, +28 %."""
        prices = seeded.sparse_prices
        assert (prices[THURSDAY], prices[FRIDAY]) == (Decimal("125"), Decimal("160")), "precondition: THURSDAY and FRIDAY are stored"

        [change] = await _live_changes(THURSDAY, _live(seeded.assets["sparse"], as_of_date=FRIDAY))

        assert change == (THURSDAY, Decimal("125"), Decimal("1"))

    @pytest.mark.parametrize("value", [Decimal("250"), Decimal("160"), Decimal("64.5")], ids=["rise", "unchanged", "fall"])
    async def test_change_is_the_house_range_change(self, seeded, value):
        """One home: whatever the quote, the change is ``range_change(reference, live value)`` — exactly 0 when the quote
        is the reference."""
        prices = seeded.sparse_prices

        [change] = await _live_changes(SATURDAY, _live(seeded.assets["sparse"], value=value))

        assert change == (SATURDAY, *_house(prices[FRIDAY], value))
        if value == prices[FRIDAY]:
            assert change[1] == 0 and change[2] == 0

    async def test_history_starting_inside_the_range(self, seeded):
        """First price 50 days after ``range_start``: the reference is that price, ``reference_date`` its day."""
        young = seeded.young_prices
        assert min(young) == YOUNG_FIRST > YOUNG_RANGE_START, "precondition: the history starts inside the range"

        [change] = await _live_changes(YOUNG_RANGE_START, _live(seeded.assets["young"]))

        assert change == (YOUNG_FIRST, *_house(young[YOUNG_FIRST], LIVE_VALUE))
        assert change[1] == LIVE_VALUE - young[YOUNG_FIRST]

    async def test_reference_in_another_currency(self, seeded):
        """The reference and the quote in different currencies: ``reference_date`` is reported, both changes are null —
        a stored SZL reference under an AMD quote, and an AMD reference under an SZL quote."""
        mixed, sparse = seeded.assets["mixed"], seeded.assets["sparse"]

        [stored_foreign] = await _live_changes(MIXED_RANGE_START, _live(mixed, as_of_date=MIXED_RANGE_AS_OF))
        [quoted_foreign] = await _live_changes(SATURDAY, _live(sparse, currency=FOREIGN))

        assert stored_foreign == (MIXED_RANGE_START, None, None), "the last price on or before MIXED_RANGE_START is the SZL row"
        assert quoted_foreign == (SATURDAY, None, None)

    async def test_no_reference(self, seeded):
        """No stored price on or before ``range_start`` nor inside ``(range_start, as_of_date]`` — the history starts
        after the quote's day, or there is none: all null."""
        young_as_of = YOUNG_FIRST - timedelta(days=1)
        assert await _price_row_count(UNKNOWN_ASSET_ID) == 0, "precondition: no price row carries UNKNOWN_ASSET_ID"

        [young] = await _live_changes(young_as_of - timedelta(days=30), _live(seeded.assets["young"], as_of_date=young_as_of))
        [unknown] = await _live_changes(SATURDAY, _live(UNKNOWN_ASSET_ID))

        assert young == NO_CHANGE and unknown == NO_CHANGE

    async def test_quote_before_range_start(self, seeded):
        """A quote dated before ``range_start`` — the provider's last close is older than the range —: all null, though a
        reference exists on ``range_start``."""
        [change] = await _live_changes(SUNDAY, _live(seeded.assets["sparse"], as_of_date=FRIDAY))

        assert change == NO_CHANGE

    @pytest.mark.parametrize(
        "missing",
        [
            pytest.param({"value": None, "currency": None, "as_of_date": None}, id="no-price"),
            pytest.param({"value": None}, id="no-value"),
            pytest.param({"currency": None}, id="no-currency"),
            pytest.param({"as_of_date": None}, id="no-as_of_date"),
        ],
    )
    async def test_result_without_a_price(self, seeded, missing):
        """A result without its value, currency or day — an error item, a quote missing a field —: all null."""
        item = _live(seeded.assets["sparse"]).model_copy(update=missing)

        [change] = await _live_changes(SATURDAY, item)

        assert change == NO_CHANGE

    async def test_bulk_each_result_as_alone(self, seeded):
        """Five results in one call, one ``range_start``: each change is what it is alone — carried, inside, a quote in
        another currency, an unknown asset, a result without a price."""
        assets = seeded.assets
        items = [
            _live(assets["sparse"]),
            _live(assets["young"]),
            _live(assets["mixed"], currency=FOREIGN),
            _live(UNKNOWN_ASSET_ID),
            FACurrentPriceItem(asset_id=assets["switched"], error="No price data available"),
        ]

        batch = await _live_changes(YOUNG_RANGE_START, *items)

        assert [change[0] for change in batch] == [YOUNG_RANGE_START, YOUNG_FIRST, YOUNG_RANGE_START, None, None], batch
        assert batch[0] != NO_CHANGE and batch[1] != NO_CHANGE and batch[2][1:] == (None, None)
        for item, change in zip(items, batch, strict=True):
            assert [change] == await _live_changes(YOUNG_RANGE_START, item), item.asset_id
