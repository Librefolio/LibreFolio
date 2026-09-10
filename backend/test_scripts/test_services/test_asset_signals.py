"""Service integration tests for signals in AssetSourceManager.get_prices_bulk."""

from __future__ import annotations

import asyncio
import time
from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

from backend.app.db.models import (  # noqa: E402
    Asset,
    AssetType,
    FxRate,
    PriceHistory,
)
from backend.app.db.session import get_async_engine  # noqa: E402
from backend.app.schemas.common import DateRangeModel  # noqa: E402
from backend.app.schemas.prices import FAPriceQueryItem  # noqa: E402
from backend.app.schemas.signals import (  # noqa: E402
    SignalCalendarReturnPointStatus,
    SignalPriceValueSource,
    SignalRequest,
    SignalStatus,
    SignalThresholdCrossingRequest,
    SignalWarningCode,
)
from backend.app.services.asset_source import AssetSourceManager  # noqa: E402


@pytest.fixture(scope="module")
def asset_signal_data():
    async def setup():
        async with AsyncSession(
            get_async_engine(),
            expire_on_commit=False,
        ) as session:
            marker = uuid4()
            stamp = marker.hex
            assets = [
                Asset(
                    display_name=f"Signal EUR A {stamp}",
                    currency="EUR",
                    asset_type=AssetType.STOCK,
                    active=True,
                ),
                Asset(
                    display_name=f"Signal EUR B {stamp}",
                    currency="EUR",
                    asset_type=AssetType.STOCK,
                    active=True,
                ),
                Asset(
                    display_name=f"Signal CAD {stamp}",
                    currency="CAD",
                    asset_type=AssetType.STOCK,
                    active=True,
                ),
                Asset(
                    display_name=f"Signal Close Only {stamp}",
                    currency="EUR",
                    asset_type=AssetType.STOCK,
                    active=True,
                ),
            ]
            session.add_all(assets)
            await session.flush()

            # The FX row is global, so give this fixture an owned date instead
            # of deleting a fixed key another worker could have created.
            start = date(1900, 1, 1) + timedelta(days=marker.int % 45_000)
            rows = []
            for offset in range(500):
                point_date = start + timedelta(days=offset)
                for asset_index, asset in enumerate(assets[:3]):
                    close = Decimal(str(100 + asset_index * 100 + offset))
                    rows.append(
                        PriceHistory(
                            asset_id=asset.id,
                            date=point_date,
                            open=close - Decimal("0.5"),
                            high=close + Decimal("1"),
                            low=close - Decimal("1"),
                            close=close,
                            volume=Decimal(1000 + offset),
                            currency=asset.currency,
                            source_plugin_key="signal_test",
                        )
                    )
                close_only = Decimal(str(50 + offset))
                rows.append(
                    PriceHistory(
                        asset_id=assets[3].id,
                        date=point_date,
                        open=None,
                        high=None,
                        low=None,
                        close=close_only,
                        volume=None,
                        currency="EUR",
                        source_plugin_key="signal_test",
                    )
                )
            session.add_all(rows)
            fx_rate = FxRate(
                base="CAD",
                quote="JPY",
                date=start,
                rate=Decimal("2"),
                source="MANUAL",
            )
            session.add(fx_rate)
            await session.commit()
            return {
                "asset_ids": [asset.id for asset in assets],
                "primary_asset_id": assets[0].id,
                "fx_rate_id": fx_rate.id,
                "start": start,
                "end": start + timedelta(days=499),
            }

    async def cleanup(data):
        async with AsyncSession(
            get_async_engine(),
            expire_on_commit=False,
        ) as session:
            await session.execute(
                delete(PriceHistory).where(
                    PriceHistory.asset_id.in_(data["asset_ids"]),
                )
            )
            await session.execute(
                delete(Asset).where(
                    Asset.id.in_(data["asset_ids"]),
                )
            )
            await session.execute(
                delete(FxRate).where(
                    FxRate.id == data["fx_rate_id"],
                )
            )
            await session.commit()

    data = asyncio.run(setup())
    yield data
    asyncio.run(cleanup(data))


def visible_range(asset_signal_data) -> DateRangeModel:
    return DateRangeModel(
        start=asset_signal_data["end"] - timedelta(days=29),
        end=asset_signal_data["end"],
    )


@pytest.mark.asyncio
async def test_asset_query_without_signals_preserves_prices(
    asset_signal_data,
):
    async with AsyncSession(
        get_async_engine(),
        expire_on_commit=False,
    ) as session:
        results = await AssetSourceManager.get_prices_bulk(
            [
                FAPriceQueryItem(
                    asset_id=asset_signal_data["asset_ids"][0],
                    date_range=visible_range(asset_signal_data),
                )
            ],
            session,
        )

    assert len(results) == 1
    assert len(results[0].prices) == 30
    assert results[0].signals == []
    assert results[0].events == []


@pytest.mark.asyncio
async def test_asset_query_computes_signal_and_annotation(
    asset_signal_data,
):
    threshold_date = asset_signal_data["end"] - timedelta(days=24)
    threshold = Decimal(str(100 + (threshold_date - asset_signal_data["start"]).days))
    async with AsyncSession(
        get_async_engine(),
        expire_on_commit=False,
    ) as session:
        results = await AssetSourceManager.get_prices_bulk(
            [
                FAPriceQueryItem(
                    asset_id=asset_signal_data["asset_ids"][0],
                    date_range=visible_range(asset_signal_data),
                    signals=[
                        SignalRequest(
                            instance_id="ema",
                            signal_code="EMA",
                            params={"period": 14},
                        )
                    ],
                    annotation_requests=[
                        SignalThresholdCrossingRequest(
                            key="price-threshold",
                            attach_to_instance_id="ema",
                            source=SignalPriceValueSource(),
                            threshold=float(threshold),
                        )
                    ],
                )
            ],
            session,
        )

    result = results[0]
    assert len(result.prices) == 30
    assert len(result.signals) == 1
    signal = result.signals[0]
    assert signal.status == SignalStatus.OK
    assert len(signal.series[0].points) == 30
    assert signal.annotations
    assert signal.annotations[0].date == threshold_date


@pytest.mark.asyncio
async def test_include_price_false_keeps_internal_signal_input(
    asset_signal_data,
):
    async with AsyncSession(
        get_async_engine(),
        expire_on_commit=False,
    ) as session:
        result = (
            await AssetSourceManager.get_prices_bulk(
                [
                    FAPriceQueryItem(
                        asset_id=asset_signal_data["asset_ids"][0],
                        date_range=visible_range(asset_signal_data),
                        include_price=False,
                        signals=[
                            SignalRequest(
                                instance_id="sma",
                                signal_code="SMA",
                                params={"period": 20},
                            )
                        ],
                    )
                ],
                session,
            )
        )[0]

    assert result.prices == []
    assert result.signals[0].status == SignalStatus.OK
    assert len(result.signals[0].series[0].points) == 30


@pytest.mark.asyncio
async def test_multi_asset_signals_use_one_bulk_price_query(
    monkeypatch,
    asset_signal_data,
):
    async with AsyncSession(
        get_async_engine(),
        expire_on_commit=False,
    ) as session:
        original_execute = session.execute
        price_queries = 0

        async def tracked_execute(statement, *args, **kwargs):
            nonlocal price_queries
            sql = str(statement)
            if "FROM price_history" in sql and "ORDER BY price_history.asset_id" in sql:
                price_queries += 1
            return await original_execute(
                statement,
                *args,
                **kwargs,
            )

        monkeypatch.setattr(
            session,
            "execute",
            tracked_execute,
        )
        results = await AssetSourceManager.get_prices_bulk(
            [
                FAPriceQueryItem(
                    asset_id=asset_id,
                    date_range=visible_range(asset_signal_data),
                    signals=[
                        SignalRequest(
                            instance_id=f"ema-{asset_id}",
                            signal_code="EMA",
                            params={"period": 14},
                        )
                    ],
                )
                for asset_id in asset_signal_data["asset_ids"][:2]
            ],
            session,
        )

    assert price_queries == 1
    assert len(results) == 2
    assert all(result.signals[0].status == SignalStatus.OK for result in results)


@pytest.mark.asyncio
async def test_risk_beta_loads_comparison_asset_in_same_bulk_query(
    monkeypatch,
    asset_signal_data,
):
    primary_id, comparison_id = asset_signal_data["asset_ids"][:2]
    async with AsyncSession(
        get_async_engine(),
        expire_on_commit=False,
    ) as session:
        original_execute = session.execute
        price_queries = 0

        async def tracked_execute(statement, *args, **kwargs):
            nonlocal price_queries
            sql = str(statement)
            if "FROM price_history" in sql and "ORDER BY price_history.asset_id" in sql:
                price_queries += 1
            return await original_execute(statement, *args, **kwargs)

        monkeypatch.setattr(session, "execute", tracked_execute)
        result = (
            await AssetSourceManager.get_prices_bulk(
                [
                    FAPriceQueryItem(
                        asset_id=primary_id,
                        date_range=visible_range(asset_signal_data),
                        signals=[
                            SignalRequest(
                                instance_id="beta",
                                signal_code="RISK_ROLLING_BETA",
                                params={
                                    "window": 10,
                                    "comparison_asset_id": comparison_id,
                                },
                            )
                        ],
                    )
                ],
                session,
            )
        )[0]

    assert price_queries == 1
    assert result.signals[0].status == SignalStatus.OK
    assert result.signals[0].risk_metadata.comparison_asset_id == comparison_id
    assert result.signals[0].risk_metadata.currency == "EUR"


@pytest.mark.asyncio
async def test_risk_beta_can_reuse_primary_as_comparison(
    asset_signal_data,
):
    asset_id = asset_signal_data["asset_ids"][0]
    async with AsyncSession(
        get_async_engine(),
        expire_on_commit=False,
    ) as session:
        result = (
            await AssetSourceManager.get_prices_bulk(
                [
                    FAPriceQueryItem(
                        asset_id=asset_id,
                        date_range=visible_range(asset_signal_data),
                        signals=[
                            SignalRequest(
                                instance_id="beta",
                                signal_code="RISK_ROLLING_BETA",
                                params={
                                    "window": 10,
                                    "comparison_asset_id": asset_id,
                                },
                            )
                        ],
                    )
                ],
                session,
            )
        )[0]

    signal = result.signals[0]
    assert signal.status == SignalStatus.OK
    assert signal.series[0].points[-1].value == pytest.approx(1.0)


@pytest.mark.asyncio
async def test_risk_signal_uses_target_currency_prepared_returns(
    asset_signal_data,
):
    async with AsyncSession(
        get_async_engine(),
        expire_on_commit=False,
    ) as session:
        result = (
            await AssetSourceManager.get_prices_bulk(
                [
                    FAPriceQueryItem(
                        asset_id=asset_signal_data["asset_ids"][2],
                        date_range=visible_range(asset_signal_data),
                        target_currency="JPY",
                        signals=[
                            SignalRequest(
                                instance_id="return",
                                signal_code="RISK_ROLLING_RETURN",
                                params={"window": 2},
                            )
                        ],
                    )
                ],
                session,
            )
        )[0]

    signal = result.signals[0]
    assert signal.status == SignalStatus.OK
    assert signal.risk_metadata.currency == "JPY"
    assert signal.risk_metadata.return_basis == "price_only"
    assert signal.data_quality.carried_forward_fx_points > 0


@pytest.mark.asyncio
async def test_target_currency_conversion_precedes_signal_compute(
    asset_signal_data,
):
    async with AsyncSession(
        get_async_engine(),
        expire_on_commit=False,
    ) as session:
        result = (
            await AssetSourceManager.get_prices_bulk(
                [
                    FAPriceQueryItem(
                        asset_id=asset_signal_data["asset_ids"][2],
                        date_range=visible_range(asset_signal_data),
                        target_currency="JPY",
                        signals=[
                            SignalRequest(
                                instance_id="sma",
                                signal_code="SMA",
                                params={"period": 2},
                            )
                        ],
                    )
                ],
                session,
            )
        )[0]

    assert all(point.currency == "JPY" for point in result.prices)
    assert result.signals[0].status == SignalStatus.OK
    last_prices = [float(point.close) for point in result.prices[-2:]]
    expected_sma = sum(last_prices) / 2
    assert result.signals[0].series[0].points[-1].value == pytest.approx(expected_sma)


@pytest.mark.asyncio
async def test_partial_target_currency_conversion_never_computes_mixed_signals(
    asset_signal_data,
):
    requested_range = visible_range(asset_signal_data)
    first_convertible_date = requested_range.start + timedelta(days=10)
    async with AsyncSession(
        get_async_engine(),
        expire_on_commit=False,
    ) as session:
        session.add(
            FxRate(
                base="CAD",
                quote="XTS",
                date=first_convertible_date,
                rate=Decimal("2"),
                source="MANUAL",
            )
        )
        await session.flush()
        result = (
            await AssetSourceManager.get_prices_bulk(
                [
                    FAPriceQueryItem(
                        asset_id=asset_signal_data["asset_ids"][2],
                        date_range=requested_range,
                        target_currency="XTS",
                        signals=[
                            SignalRequest(
                                instance_id="ema",
                                signal_code="EMA",
                                params={"period": 14},
                            )
                        ],
                    )
                ],
                session,
            )
        )[0]

    assert {point.currency for point in result.prices} == {"CAD", "XTS"}
    assert any("mixed currencies" in error for error in result.errors)
    assert result.signals[0].status == SignalStatus.UNAVAILABLE
    assert result.signals[0].series == []


@pytest.mark.asyncio
async def test_target_currency_equal_to_native_remains_signal_coherent(
    asset_signal_data,
):
    async with AsyncSession(
        get_async_engine(),
        expire_on_commit=False,
    ) as session:
        result = (
            await AssetSourceManager.get_prices_bulk(
                [
                    FAPriceQueryItem(
                        asset_id=asset_signal_data["asset_ids"][0],
                        date_range=visible_range(asset_signal_data),
                        target_currency="EUR",
                        signals=[
                            SignalRequest(
                                instance_id="ema",
                                signal_code="EMA",
                                params={"period": 14},
                            )
                        ],
                    )
                ],
                session,
            )
        )[0]

    assert {point.currency for point in result.prices} == {"EUR"}
    assert result.signals[0].status == SignalStatus.OK


@pytest.mark.asyncio
async def test_missing_target_currency_rate_makes_signals_unavailable(
    asset_signal_data,
):
    async with AsyncSession(
        get_async_engine(),
        expire_on_commit=False,
    ) as session:
        result = (
            await AssetSourceManager.get_prices_bulk(
                [
                    FAPriceQueryItem(
                        asset_id=asset_signal_data["asset_ids"][2],
                        date_range=visible_range(asset_signal_data),
                        target_currency="BMD",
                        signals=[
                            SignalRequest(
                                instance_id="ema",
                                signal_code="EMA",
                                params={"period": 14},
                            )
                        ],
                    )
                ],
                session,
            )
        )[0]

    assert result.errors
    assert result.signals[0].status == SignalStatus.UNAVAILABLE


@pytest.mark.asyncio
async def test_missing_ohlc_is_unavailable_without_breaking_prices(
    asset_signal_data,
):
    async with AsyncSession(
        get_async_engine(),
        expire_on_commit=False,
    ) as session:
        result = (
            await AssetSourceManager.get_prices_bulk(
                [
                    FAPriceQueryItem(
                        asset_id=asset_signal_data["asset_ids"][3],
                        date_range=visible_range(asset_signal_data),
                        signals=[
                            SignalRequest(
                                instance_id="atr",
                                signal_code="ATR",
                                params={"period": 14},
                            )
                        ],
                    )
                ],
                session,
            )
        )[0]

    assert len(result.prices) == 30
    assert result.signals[0].status == SignalStatus.UNAVAILABLE


@pytest.mark.asyncio
async def test_invalid_signal_is_isolated_from_valid_signal_and_prices(
    asset_signal_data,
):
    async with AsyncSession(
        get_async_engine(),
        expire_on_commit=False,
    ) as session:
        result = (
            await AssetSourceManager.get_prices_bulk(
                [
                    FAPriceQueryItem(
                        asset_id=asset_signal_data["asset_ids"][0],
                        date_range=visible_range(asset_signal_data),
                        signals=[
                            SignalRequest(
                                instance_id="invalid",
                                signal_code="EMA",
                                params={"period": 1},
                            ),
                            SignalRequest(
                                instance_id="valid",
                                signal_code="EMA",
                                params={"period": 14},
                            ),
                        ],
                    )
                ],
                session,
            )
        )[0]

    assert len(result.prices) == 30
    assert result.signals[0].status == SignalStatus.FAILED
    assert result.signals[1].status == SignalStatus.OK


@pytest.mark.asyncio
async def test_duplicate_asset_items_use_seed_for_each_load_range():
    async with AsyncSession(
        get_async_engine(),
        expire_on_commit=False,
    ) as session:
        asset = Asset(
            display_name=f"Signal Duplicate {time.time_ns()}",
            currency="EUR",
            asset_type=AssetType.STOCK,
            active=True,
        )
        session.add(asset)
        await session.flush()
        start = date(2026, 1, 1)
        session.add_all(
            [
                PriceHistory(
                    asset_id=asset.id,
                    date=start,
                    close=Decimal("10"),
                    currency="EUR",
                    source_plugin_key="signal_test",
                ),
                PriceHistory(
                    asset_id=asset.id,
                    date=start + timedelta(days=40),
                    close=Decimal("50"),
                    currency="EUR",
                    source_plugin_key="signal_test",
                ),
                PriceHistory(
                    asset_id=asset.id,
                    date=start + timedelta(days=60),
                    close=Decimal("70"),
                    currency="EUR",
                    source_plugin_key="signal_test",
                ),
            ]
        )
        await session.commit()

        results = await AssetSourceManager.get_prices_bulk(
            [
                FAPriceQueryItem(
                    asset_id=asset.id,
                    date_range=DateRangeModel(
                        start=start + timedelta(days=50),
                        end=start + timedelta(days=60),
                    ),
                ),
                FAPriceQueryItem(
                    asset_id=asset.id,
                    date_range=DateRangeModel(
                        start=start + timedelta(days=55),
                        end=start + timedelta(days=60),
                    ),
                    signals=[
                        SignalRequest(
                            instance_id="sma",
                            signal_code="SMA",
                            params={"period": 20},
                        )
                    ],
                ),
            ],
            session,
        )

    first_point = results[0].prices[0]
    assert first_point.close == Decimal("50")
    assert first_point.backward_fill_info.actual_rate_date == start + timedelta(days=40)
    assert results[1].signals[0].status in {
        SignalStatus.OK,
        SignalStatus.PARTIAL,
    }


# =============================================================================
# I10 — ASSET_CALENDAR_ROLLING_RETURN through the Asset adapter
#
# The plugin itself is pure. Everything it depends on — dense daily resolution,
# target-currency conversion, and enough PRE-VISIBLE CALENDAR DAYS to reach
# t - N — is the adapter's job, so it can only be verified here.
#
# Per-test rows are flushed and rolled back; the shared module fixture removes
# its committed assets, prices, and FX rate after the module.
# =============================================================================

CALENDAR_SIGNAL_CODE = "ASSET_CALENDAR_ROLLING_RETURN"
CALENDAR_SERIES_KEY = "calendar_return"


def calendar_series(signal):
    return next(series for series in signal.series if series.key == CALENDAR_SERIES_KEY)


def point_on(series, target: date):
    return next(point for point in series.points if point.date == target)


def price_on(prices, target: date):
    return next(price for price in prices if price.date == target)


def result_for_asset(results, asset_id: int):
    return next(result for result in results if result.asset_id == asset_id)


@pytest.mark.asyncio
async def test_calendar_return_warmup_loads_pre_visible_calendar_days(
    asset_signal_data,
):
    """The visible range is 30 days and the window is 30 days, so EVERY visible
    point needs a price from before the visible range. A points-derived warm-up
    that stopped short would leave the early visible points null and still look
    like a plausible result."""
    asset_id = asset_signal_data["primary_asset_id"]
    requested_range = visible_range(asset_signal_data)
    async with AsyncSession(
        get_async_engine(),
        expire_on_commit=False,
    ) as session:
        results = await AssetSourceManager.get_prices_bulk(
            [
                FAPriceQueryItem(
                    asset_id=asset_id,
                    date_range=requested_range,
                    signals=[
                        SignalRequest(
                            instance_id="calendar",
                            signal_code=CALENDAR_SIGNAL_CODE,
                            params={"window_days": 30},
                        )
                    ],
                )
            ],
            session,
        )
    result = result_for_asset(results, asset_id)

    signal = next(item for item in result.signals if item.instance_id == "calendar")
    assert signal.status == SignalStatus.OK
    assert signal.warmup.complete is True
    assert SignalWarningCode.UNDEFINED_METRIC_WINDOW not in {warning.code for warning in signal.warnings}
    series = calendar_series(signal)
    assert [point.date for point in series.points] == [requested_range.start + timedelta(days=offset) for offset in range(30)]
    for point in series.points:
        offset = (point.date - asset_signal_data["start"]).days
        # Fixture close for this asset is 100 + offset, one row per calendar day.
        assert point.value == pytest.approx(((100.0 + offset) / (70.0 + offset) - 1) * 100)
        assert point.provenance.status == SignalCalendarReturnPointStatus.AVAILABLE
        assert point.provenance.reference_target_date == point.date - timedelta(days=30)
        assert point.provenance.current_price_date == point.date
        assert point.provenance.current_price_days_back == 0


@pytest.mark.asyncio
async def test_calendar_return_consumes_target_currency_converted_points():
    """Conversion happens BEFORE the plugin runs, so a rate that changes inside
    the loaded window changes the calendar return. With a constant rate the
    ratio would be identical to the native one and this would prove nothing —
    hence two rates, and an explicit assertion against the native value."""
    marker = uuid4()
    start = date(1900, 1, 1) + timedelta(days=marker.int % 45_000)
    current_date = start + timedelta(days=99)
    requested_range = DateRangeModel(
        start=current_date - timedelta(days=59),
        end=current_date,
    )
    late_rate_date = current_date - timedelta(days=19)
    reference_date = current_date - timedelta(days=30)
    async with AsyncSession(
        get_async_engine(),
        expire_on_commit=False,
    ) as session:
        asset = Asset(
            display_name=f"Calendar Converted {marker.hex}",
            currency="CAD",
            asset_type=AssetType.STOCK,
            active=True,
        )
        session.add(asset)
        await session.flush()
        session.add_all(
            [
                PriceHistory(
                    asset_id=asset.id,
                    date=start + timedelta(days=offset),
                    close=Decimal(str(300 + offset)),
                    currency="CAD",
                    source_plugin_key="signal_test",
                )
                for offset in range(100)
            ]
        )
        session.add_all(
            [
                FxRate(
                    base="CAD",
                    quote="XTS",
                    date=start,
                    rate=Decimal("2"),
                    source="MANUAL",
                ),
                FxRate(
                    base="CAD",
                    quote="XTS",
                    date=late_rate_date,
                    rate=Decimal("5"),
                    source="MANUAL",
                ),
            ]
        )
        await session.flush()
        results = await AssetSourceManager.get_prices_bulk(
            [
                FAPriceQueryItem(
                    asset_id=asset.id,
                    date_range=requested_range,
                    target_currency="XTS",
                    signals=[
                        SignalRequest(
                            instance_id="calendar",
                            signal_code=CALENDAR_SIGNAL_CODE,
                            params={"window_days": 30},
                        )
                    ],
                )
            ],
            session,
        )
        result = result_for_asset(results, asset.id)
        # All rows belong to this transaction and disappear together.
        await session.rollback()

    assert {point.currency for point in result.prices} == {"XTS"}
    signal = next(item for item in result.signals if item.instance_id == "calendar")
    assert signal.status == SignalStatus.OK

    converted_current = float(price_on(result.prices, current_date).close)
    converted_reference = float(price_on(result.prices, reference_date).close)
    native_current = 300.0 + (current_date - start).days
    native_reference = 300.0 + (reference_date - start).days

    point = point_on(calendar_series(signal), current_date)
    assert point.value == pytest.approx((converted_current / converted_reference - 1) * 100)
    assert point.value != pytest.approx((native_current / native_reference - 1) * 100)
    # The reference sits before the rate change and keeps its own FX provenance.
    assert point.provenance.status == SignalCalendarReturnPointStatus.AVAILABLE
    assert point.provenance.current_fx_date == late_rate_date
    assert point.provenance.current_fx_days_back == 19
    assert point.provenance.reference_fx_date == start
    assert point.provenance.reference_fx_days_back == (reference_date - start).days
    assert point.provenance.reference_price_date == reference_date
    assert point.provenance.reference_price_days_back == 0


@pytest.mark.asyncio
async def test_calendar_reference_reports_the_backward_resolved_observation():
    """The reference date itself has no stored price: the adapter carries the
    last observation forward, and the point must say so instead of pretending
    it priced 2026-04-07."""
    start = date(2026, 3, 1)
    hole = {start + timedelta(days=offset) for offset in (35, 36, 37)}
    requested_range = DateRangeModel(
        start=start + timedelta(days=40),
        end=start + timedelta(days=49),
    )
    async with AsyncSession(
        get_async_engine(),
        expire_on_commit=False,
    ) as session:
        asset = Asset(
            display_name=f"Calendar Gap {uuid4().hex}",
            currency="EUR",
            asset_type=AssetType.STOCK,
            active=True,
        )
        session.add(asset)
        await session.flush()
        session.add_all(
            [
                PriceHistory(
                    asset_id=asset.id,
                    date=start + timedelta(days=offset),
                    close=Decimal(str(100 + offset)),
                    currency="EUR",
                    source_plugin_key="signal_test",
                )
                for offset in range(50)
                if start + timedelta(days=offset) not in hole
            ]
        )
        await session.flush()
        results = await AssetSourceManager.get_prices_bulk(
            [
                FAPriceQueryItem(
                    asset_id=asset.id,
                    date_range=requested_range,
                    signals=[
                        SignalRequest(
                            instance_id="calendar",
                            signal_code=CALENDAR_SIGNAL_CODE,
                            params={"window_days": 7},
                        )
                    ],
                )
            ],
            session,
        )
        result = result_for_asset(results, asset.id)
        # Nothing is committed: the asset and its prices die with this session.
        await session.rollback()

    signal = next(item for item in result.signals if item.instance_id == "calendar")
    assert signal.status == SignalStatus.OK
    series = calendar_series(signal)
    assert [point.date for point in series.points] == [requested_range.start + timedelta(days=offset) for offset in range(10)]

    carried = point_on(series, start + timedelta(days=44))
    assert carried.value == pytest.approx((144.0 / 134.0 - 1) * 100)
    assert carried.provenance.status == SignalCalendarReturnPointStatus.AVAILABLE
    assert carried.provenance.reference_target_date == start + timedelta(days=37)
    assert carried.provenance.reference_price_date == start + timedelta(days=34)
    assert carried.provenance.reference_price_days_back == 3
    assert carried.provenance.current_price_date == start + timedelta(days=44)
    assert carried.provenance.current_price_days_back == 0
    assert carried.provenance.current_fx_date is None
    assert carried.provenance.reference_fx_date is None

    observed = point_on(series, start + timedelta(days=41))
    assert observed.value == pytest.approx((141.0 / 134.0 - 1) * 100)
    assert observed.provenance.reference_price_date == start + timedelta(days=34)
    assert observed.provenance.reference_price_days_back == 0


@pytest.mark.asyncio
async def test_calendar_signal_only_response_stays_valid(
    asset_signal_data,
):
    asset_id = asset_signal_data["primary_asset_id"]
    async with AsyncSession(
        get_async_engine(),
        expire_on_commit=False,
    ) as session:
        results = await AssetSourceManager.get_prices_bulk(
            [
                FAPriceQueryItem(
                    asset_id=asset_id,
                    date_range=visible_range(asset_signal_data),
                    include_price=False,
                    signals=[
                        SignalRequest(
                            instance_id="calendar",
                            signal_code=CALENDAR_SIGNAL_CODE,
                            params={"window_days": 90},
                        )
                    ],
                )
            ],
            session,
        )
    result = result_for_asset(results, asset_id)

    assert result.prices == []
    signal = next(item for item in result.signals if item.instance_id == "calendar")
    assert signal.status == SignalStatus.OK
    series = calendar_series(signal)
    assert len(series.points) == 30
    probe = point_on(series, asset_signal_data["end"])
    offset = (asset_signal_data["end"] - asset_signal_data["start"]).days
    assert probe.value == pytest.approx(((100.0 + offset) / (10.0 + offset) - 1) * 100)
    assert probe.provenance.reference_target_date == asset_signal_data["end"] - timedelta(days=90)
