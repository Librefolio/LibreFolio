"""Service integration tests for signals in AssetSourceManager.get_prices_bulk."""

from __future__ import annotations

import asyncio
import time
from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
import pytest_asyncio
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
    SignalAvailabilityReason,
    SignalCalendarReturnPointStatus,
    SignalDomain,
    SignalExecutionContext,
    SignalPriceValueSource,
    SignalRequest,
    SignalStatus,
    SignalThresholdCrossingRequest,
    SignalWarningCode,
)
from backend.app.services import market_calendar  # noqa: E402
from backend.app.services.asset_source import AssetSourceManager  # noqa: E402
from backend.app.services.asset_sources import price_query as price_query_module  # noqa: E402
from backend.app.services.asset_sources.price_query import PriceQueryOperations  # noqa: E402
from backend.app.services.provider_registry import SignalPluginRegistry  # noqa: E402


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
async def test_partial_target_currency_conversion_passes_calendar_its_valid_subset(
    asset_signal_data,
):
    asset_id = asset_signal_data["asset_ids"][2]
    requested_range = visible_range(asset_signal_data)
    window_days = 7
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
        results = await AssetSourceManager.get_prices_bulk(
            [
                FAPriceQueryItem(
                    asset_id=asset_id,
                    date_range=requested_range,
                    target_currency="XTS",
                    signals=[
                        SignalRequest(
                            instance_id="calendar",
                            signal_code=CALENDAR_SIGNAL_CODE,
                            params={"window_days": window_days},
                        ),
                        SignalRequest(
                            instance_id="ema",
                            signal_code="EMA",
                            params={"period": 14},
                        ),
                    ],
                )
            ],
            session,
        )
        result = next(item for item in results if item.asset_id == asset_id)

    assert {point.currency for point in result.prices} == {"CAD", "XTS"}
    assert any("mixed currencies" in error for error in result.errors)
    signals_by_id = {signal.instance_id: signal for signal in result.signals}
    calendar = signals_by_id["calendar"]
    ema = signals_by_id["ema"]

    assert calendar.status == SignalStatus.PARTIAL
    assert calendar.availability.reason_code == SignalAvailabilityReason.PARTIAL_UNDEFINED_METRIC
    assert calendar.error is None
    calendar_dates = [point.date for point in calendar_series(calendar).points]
    expected_first = first_convertible_date + timedelta(days=window_days)
    assert calendar_dates == [expected_first + timedelta(days=offset) for offset in range((requested_range.end - expected_first).days + 1)]
    assert calendar_dates == sorted(set(calendar_dates))
    assert all(requested_range.start <= point_date <= requested_range.end for point_date in calendar_dates)
    first = point_on(calendar_series(calendar), expected_first)
    current_offset = (expected_first - asset_signal_data["start"]).days
    reference_offset = (first_convertible_date - asset_signal_data["start"]).days
    assert first.value == pytest.approx(((300.0 + current_offset) / (300.0 + reference_offset) - 1) * 100)
    assert first.provenance.reference_target_date == first_convertible_date

    # Dense legacy plugins keep their own contract: the Calendar opt-in does
    # not compact or otherwise change a sibling's input policy.
    assert ema.status == SignalStatus.UNAVAILABLE
    assert ema.availability.reason_code == SignalAvailabilityReason.INSUFFICIENT_INPUT_COVERAGE
    assert ema.series == []


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
async def test_duplicate_asset_items_use_seed_for_each_load_range(
    asset_signal_rollback_session,
):
    """Two items for one asset, each with its own load range and its own seed.

    The first opens on a day without a row and is seeded from inside the bulk
    window; the second, warmed up for SMA 20, opens before every row of the
    window and is seeded from the row before it. Twenty-five genuine sessions
    precede its visible range, since the SMA counts sessions, not the
    calendar copies of a seed.
    """
    session = asset_signal_rollback_session
    asset = Asset(
        display_name=f"Signal Duplicate {time.time_ns()}",
        currency="EUR",
        asset_type=AssetType.STOCK,
        active=True,
    )
    session.add(asset)
    await session.flush()
    start = date(2026, 1, 1)
    closes = {
        start: Decimal("10"),
        **{start + timedelta(days=offset): Decimal(20 + offset) for offset in range(16, 40)},
        start + timedelta(days=40): Decimal("50"),
        start + timedelta(days=60): Decimal("70"),
    }
    session.add_all(
        [
            PriceHistory(
                asset_id=asset.id,
                date=day,
                close=close,
                currency="EUR",
                source_plugin_key="signal_test",
            )
            for day, close in closes.items()
        ]
    )
    await session.flush()

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
    signal = results[1].signals[0]
    # SMA 20 loads forty calendar days: its range opens on day 15, where no row exists, so
    # only the seed from before the bulk window (day 0) can make it start there.
    assert signal.availability.input_coverage.first_available_date == start + timedelta(days=15)
    assert signal.status == SignalStatus.OK


# =============================================================================
# I10 — ASSET_CALENDAR_ROLLING_RETURN through the Asset adapter
#
# The plugin itself is pure. Loading N pre-visible calendar days, resolving
# source observations, and target-currency conversion are the adapter's job.
# Signal output is still sliced to the selected range.
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
async def test_calendar_return_warmup_loads_pre_range_calendar_days(
    asset_signal_data,
):
    """Every selected point resolves its exact t-N reference from factual
    pre-range history loaded by the adapter."""
    asset_id = asset_signal_data["primary_asset_id"]
    window_days = 30
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
                            params={"window_days": window_days},
                        )
                    ],
                )
            ],
            session,
        )
    result = result_for_asset(results, asset_id)

    assert [point.date for point in result.prices] == [requested_range.start + timedelta(days=offset) for offset in range(30)]
    signal = next(item for item in result.signals if item.instance_id == "calendar")
    assert signal.status == SignalStatus.OK
    assert signal.availability.reason_code is None
    assert signal.availability.required_points == window_days
    assert signal.warmup.requirement.model_dump(mode="python") == {
        "minimum_points": 1,
        "stabilization_points": window_days - 1,
        "total_points": window_days,
        "normalized_tolerance": 1e-6,
        "full_history": False,
    }
    assert signal.warmup.loaded_points == window_days + 30
    assert signal.warmup.complete is True
    assert signal.warmup.used_points == window_days
    assert signal.warnings == []
    series = calendar_series(signal)
    assert [point.date for point in series.points] == [requested_range.start + timedelta(days=offset) for offset in range(30)]
    for point in series.points:
        current_offset = (point.date - asset_signal_data["start"]).days
        reference_offset = current_offset - window_days
        # Fixture close is 100 + offset, one row per calendar day.
        assert point.value == pytest.approx(((100.0 + current_offset) / (100.0 + reference_offset) - 1) * 100)
        assert point.provenance.status == SignalCalendarReturnPointStatus.AVAILABLE
        assert point.provenance.reference_target_date == point.date - timedelta(days=window_days)
        assert point.provenance.current_price_date == point.date
        assert point.provenance.current_price_days_back == 0


@pytest.mark.asyncio
async def test_calendar_return_consumes_target_currency_converted_points():
    """Conversion happens BEFORE the plugin runs, so a rate that changes inside
    the loaded window changes the calendar return. With a constant rate the
    ratio would be identical to the native one and this would prove nothing —
    hence two rates, a non-legacy 14-day window, and an explicit assertion
    against the native value."""
    marker = uuid4()
    start = date(1900, 1, 1) + timedelta(days=marker.int % 45_000)
    current_date = start + timedelta(days=99)
    requested_range = DateRangeModel(
        start=current_date - timedelta(days=59),
        end=current_date,
    )
    late_rate_date = current_date - timedelta(days=7)
    reference_date = current_date - timedelta(days=14)
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
                            params={"window_days": 14},
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
    assert signal.normalized_params == {"window_days": 14}

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
    assert point.provenance.current_fx_days_back == 7
    assert point.provenance.reference_fx_date == start
    assert point.provenance.reference_fx_days_back == (reference_date - start).days
    assert point.provenance.reference_price_date == reference_date
    assert point.provenance.reference_price_days_back == 0


@pytest.mark.asyncio
async def test_calendar_interior_fx_gap_is_sparse_with_typed_reference_cause():
    window_days = 7
    marker = uuid4()
    load_start = date(1800, 1, 1) + timedelta(days=marker.int % 20_000)
    selected_start = load_start + timedelta(days=window_days)
    selected_end = selected_start + timedelta(days=10)
    missing_fx_date = selected_start + timedelta(days=2)
    affected_reference_date = missing_fx_date + timedelta(days=window_days)
    requested_range = DateRangeModel(
        start=selected_start,
        end=selected_end,
    )

    async with AsyncSession(
        get_async_engine(),
        expire_on_commit=False,
    ) as session:
        asset = Asset(
            display_name=f"Calendar Interior FX {marker.hex}",
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
                    date=load_start + timedelta(days=offset),
                    close=Decimal(str(100 + offset)),
                    currency=("BMD" if load_start + timedelta(days=offset) == missing_fx_date else "CAD"),
                    source_plugin_key="signal_test",
                )
                for offset in range((selected_end - load_start).days + 1)
            ]
        )
        session.add(
            FxRate(
                base="CAD",
                quote="XTS",
                date=load_start,
                rate=Decimal("2"),
                source="MANUAL",
            )
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
                            params={"window_days": window_days},
                        )
                    ],
                )
            ],
            session,
        )
        result = next(item for item in results if item.asset_id == asset.id)
        await session.rollback()

    assert {point.currency for point in result.prices} == {"BMD", "XTS"}
    assert any("mixed currencies" in error for error in result.errors)
    calendar = next(signal for signal in result.signals if signal.instance_id == "calendar")
    assert calendar.status == SignalStatus.PARTIAL
    assert calendar.availability.reason_code == SignalAvailabilityReason.PARTIAL_UNDEFINED_METRIC
    assert calendar.error is None
    assert SignalWarningCode.DATA_GAP in {warning.code for warning in calendar.warnings}
    assert SignalWarningCode.UNDEFINED_METRIC_WINDOW in {warning.code for warning in calendar.warnings}

    series = calendar_series(calendar)
    expected_dates = [selected_start + timedelta(days=offset) for offset in range((selected_end - selected_start).days + 1) if selected_start + timedelta(days=offset) != missing_fx_date]
    assert [point.date for point in series.points] == expected_dates
    assert [point.date for point in series.points] == sorted({point.date for point in series.points})
    assert all(selected_start <= point.date <= selected_end for point in series.points)
    assert all(point.value is not None for point in series.points if point.date != affected_reference_date)
    affected = point_on(series, affected_reference_date)
    assert affected.value is None
    assert affected.provenance.status == SignalCalendarReturnPointStatus.MISSING_REFERENCE
    assert affected.provenance.reference_target_date == missing_fx_date
    assert affected.provenance.reference_price_date is None


@pytest.mark.asyncio
async def test_calendar_reference_reports_the_backward_resolved_observation():
    """The reference date itself has no stored price: the adapter carries the
    factual pre-range observation forward, and the point must say so instead
    of pretending the target date was observed."""
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
    window_days = 90
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
                    include_price=False,
                    signals=[
                        SignalRequest(
                            instance_id="calendar",
                            signal_code=CALENDAR_SIGNAL_CODE,
                            params={"window_days": window_days},
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
    assert signal.warnings == []
    assert signal.availability.required_points == window_days
    assert signal.warmup.requirement.total_points == window_days
    assert signal.warmup.used_points == window_days
    assert signal.warmup.complete is True
    series = calendar_series(signal)
    assert [point.date for point in series.points] == [requested_range.start + timedelta(days=offset) for offset in range(30)]
    probe = point_on(series, asset_signal_data["end"])
    offset = (asset_signal_data["end"] - asset_signal_data["start"]).days
    assert probe.value == pytest.approx(((100.0 + offset) / (100.0 + offset - window_days) - 1) * 100)
    assert probe.provenance.reference_target_date == asset_signal_data["end"] - timedelta(days=window_days)


# =============================================================================
# I60G — primary and peer Calendar histories are independently factual
# =============================================================================


@pytest_asyncio.fixture
async def asset_signal_rollback_session():
    async with AsyncSession(
        get_async_engine(),
        expire_on_commit=False,
    ) as session:
        try:
            yield session
        finally:
            await session.rollback()


@pytest_asyncio.fixture
async def calendar_sibling_assets(
    asset_signal_rollback_session,
):
    window_days = 7
    selected_start = date(2026, 4, 1)
    selected_end = selected_start + timedelta(days=14)
    warmup_start = selected_start - timedelta(days=window_days)
    partial_start = selected_start + timedelta(days=2)
    unavailable_start = selected_end - timedelta(days=3)
    marker = uuid4().hex
    primary = Asset(
        display_name=f"I60G Calendar Primary {marker}",
        currency="EUR",
        asset_type=AssetType.STOCK,
        active=True,
    )
    partial_peer = Asset(
        display_name=f"I60G Calendar Partial Peer {marker}",
        currency="EUR",
        asset_type=AssetType.STOCK,
        active=True,
    )
    unavailable_peer = Asset(
        display_name=f"I60G Calendar Unavailable Peer {marker}",
        currency="EUR",
        asset_type=AssetType.STOCK,
        active=True,
    )
    asset_signal_rollback_session.add_all(
        [
            primary,
            partial_peer,
            unavailable_peer,
        ]
    )
    await asset_signal_rollback_session.flush()

    primary_base = Decimal("1000")
    partial_base = Decimal("200")
    rows = []
    for offset in range((selected_end - warmup_start).days + 1):
        point_date = warmup_start + timedelta(days=offset)
        rows.append(
            PriceHistory(
                asset_id=primary.id,
                date=point_date,
                close=primary_base + offset,
                currency="EUR",
                source_plugin_key="signal_test",
            )
        )
    for offset in range((selected_end - partial_start).days + 1):
        rows.append(
            PriceHistory(
                asset_id=partial_peer.id,
                date=partial_start + timedelta(days=offset),
                close=partial_base + offset,
                currency="EUR",
                source_plugin_key="signal_test",
            )
        )
    for offset in range((selected_end - unavailable_start).days + 1):
        rows.append(
            PriceHistory(
                asset_id=unavailable_peer.id,
                date=unavailable_start + timedelta(days=offset),
                close=Decimal("500") + offset,
                currency="EUR",
                source_plugin_key="signal_test",
            )
        )
    asset_signal_rollback_session.add_all(rows)
    await asset_signal_rollback_session.flush()

    return {
        "window_days": window_days,
        "selected_start": selected_start,
        "selected_end": selected_end,
        "warmup_start": warmup_start,
        "partial_start": partial_start,
        "primary_base": primary_base,
        "partial_base": partial_base,
        "primary_asset_id": primary.id,
        "partial_asset_id": partial_peer.id,
        "unavailable_asset_id": unavailable_peer.id,
    }


@pytest.mark.asyncio
async def test_calendar_assets_keep_independent_ok_partial_and_unavailable_subsets(
    asset_signal_rollback_session,
    calendar_sibling_assets,
):
    """A late or unavailable peer cannot suppress the factual primary line."""
    window_days = calendar_sibling_assets["window_days"]
    selected_range = DateRangeModel(
        start=calendar_sibling_assets["selected_start"],
        end=calendar_sibling_assets["selected_end"],
    )
    asset_ids = [
        calendar_sibling_assets["primary_asset_id"],
        calendar_sibling_assets["partial_asset_id"],
        calendar_sibling_assets["unavailable_asset_id"],
    ]

    results = await AssetSourceManager.get_prices_bulk(
        [
            FAPriceQueryItem(
                asset_id=asset_id,
                date_range=selected_range,
                include_price=(asset_id == calendar_sibling_assets["primary_asset_id"]),
                include_events=False,
                target_currency="EUR",
                signals=[
                    SignalRequest(
                        instance_id="calendar",
                        signal_code=CALENDAR_SIGNAL_CODE,
                        params={"window_days": window_days},
                    )
                ],
            )
            for asset_id in asset_ids
        ],
        asset_signal_rollback_session,
    )
    results_by_asset = {result.asset_id: result for result in results}
    primary_result = results_by_asset[calendar_sibling_assets["primary_asset_id"]]
    partial_result = results_by_asset[calendar_sibling_assets["partial_asset_id"]]
    unavailable_result = results_by_asset[calendar_sibling_assets["unavailable_asset_id"]]

    assert primary_result.errors == []
    assert partial_result.errors == []
    assert unavailable_result.errors == []
    assert partial_result.prices == []
    assert unavailable_result.prices == []
    signals_by_asset = {asset_id: next(signal for signal in results_by_asset[asset_id].signals if signal.instance_id == "calendar") for asset_id in asset_ids}
    primary = signals_by_asset[calendar_sibling_assets["primary_asset_id"]]
    partial = signals_by_asset[calendar_sibling_assets["partial_asset_id"]]
    unavailable = signals_by_asset[calendar_sibling_assets["unavailable_asset_id"]]

    assert primary.status == SignalStatus.OK
    assert primary.availability.reason_code is None
    primary_series = calendar_series(primary)
    primary_dates = [selected_range.start + timedelta(days=offset) for offset in range((selected_range.end - selected_range.start).days + 1)]
    assert [point.date for point in primary_series.points] == primary_dates
    primary_first = point_on(primary_series, selected_range.start)
    assert primary_first.value == pytest.approx(((float(calendar_sibling_assets["primary_base"]) + window_days) / float(calendar_sibling_assets["primary_base"]) - 1) * 100)
    assert primary_first.provenance.reference_target_date == calendar_sibling_assets["warmup_start"]

    assert partial.status == SignalStatus.PARTIAL
    assert partial.availability.reason_code == SignalAvailabilityReason.PARTIAL_UNDEFINED_METRIC
    partial_series = calendar_series(partial)
    first_partial_date = calendar_sibling_assets["partial_start"] + timedelta(days=window_days)
    partial_dates = [first_partial_date + timedelta(days=offset) for offset in range((selected_range.end - first_partial_date).days + 1)]
    assert [point.date for point in partial_series.points] == partial_dates
    assert [point.date for point in partial_series.points] == sorted({point.date for point in partial_series.points})
    partial_first = point_on(partial_series, first_partial_date)
    assert partial_first.value == pytest.approx(((float(calendar_sibling_assets["partial_base"]) + window_days) / float(calendar_sibling_assets["partial_base"]) - 1) * 100)
    assert partial_first.provenance.reference_target_date == calendar_sibling_assets["partial_start"]

    assert unavailable.status == SignalStatus.UNAVAILABLE
    assert unavailable.availability.reason_code == SignalAvailabilityReason.INSUFFICIENT_HISTORY
    assert unavailable.error is None
    assert unavailable.series == []


# =============================================================================
# Quote days (developer's decision of 30/09/2026)
#
# «Sui giorni di quotazione, come la definizione standard: SMA 200 = 200 sedute.»
# In this adapter a stored carry — a weekend or union-holiday row whose close
# repeats the row before it exactly, as justETF stores them — reaches the signal
# service marked as backfilled, by the rule of
# `market_calendar.is_market_closed_repeat` and the table the adapter awaits
# once per `get_prices_bulk` call. Session plugins then load twice their
# sessions in calendar days; full-history plans and the prepared multiplier are
# unchanged.
#
# The holiday table is served, never built: a QuantLib build in a spawn process
# has no place in a unit, and a served table makes the holidays exact. The
# seven-day source's rows are flushed and rolled back.
# =============================================================================

NOT_PASSED = object()
SEVEN_DAY_FIRST_DAY = date(2024, 1, 1)  # a Monday
SEVEN_DAY_VISIBLE = DateRangeModel(start=date(2024, 3, 4), end=date(2024, 3, 31))  # Monday to Sunday
SEVEN_DAY_SMA_PERIOD = 10
MOVING_SATURDAY = date(2024, 3, 9)
TABLE_DAY_THAT_MOVES = date(2024, 3, 14)  # a Thursday in the served table, quoted with a new close
TABLE_DAY_THAT_REPEATS = date(2024, 3, 20)  # a Wednesday in the served table, repeating Tuesday
FLAT_WEEKDAY = date(2024, 3, 26)  # a Tuesday repeating Monday, in no table


@pytest.fixture
def served_market_holidays(monkeypatch):
    """Serve a known holiday table where the adapter awaits it, and count the awaits."""
    served = SimpleNamespace(table=frozenset(), awaits=0)

    async def serve() -> frozenset[date]:
        served.awaits += 1
        return served.table

    monkeypatch.setattr(price_query_module, "ensure_market_holidays", serve, raising=False)
    monkeypatch.setattr(market_calendar, "ensure_market_holidays", serve)
    return served


def seven_day_closes(
    *,
    moving_saturdays: frozenset[date] = frozenset(),
    repeating_weekdays: frozenset[date] = frozenset(),
) -> dict[date, Decimal]:
    """One close per calendar day, the way a seven-day source stores them.

    A weekend day repeats the row before it exactly unless it is a moving
    Saturday; a weekday moves unless it is listed as repeating.
    """
    closes: dict[date, Decimal] = {}
    previous = Decimal("0")
    moves = 0
    day = SEVEN_DAY_FIRST_DAY
    while day <= SEVEN_DAY_VISIBLE.end:
        if day in moving_saturdays:
            close = previous + Decimal("1.25")
        elif day.weekday() >= 5 or day in repeating_weekdays:
            close = previous
        else:
            close = Decimal(10_000 + 17 * moves + 90 * ((3 * moves) % 5)) / Decimal(100)
            moves += 1
        closes[day] = close
        previous = close
        day += timedelta(days=1)
    return closes


@pytest_asyncio.fixture
async def seven_day_asset(asset_signal_rollback_session):
    """Create a close-only asset whose rows are the given closes."""

    async def create(closes: dict[date, Decimal]) -> int:
        asset = Asset(
            display_name=f"Quote Days Seven-Day Source {uuid4().hex}",
            currency="EUR",
            asset_type=AssetType.ETF,
            active=True,
        )
        asset_signal_rollback_session.add(asset)
        await asset_signal_rollback_session.flush()
        asset_signal_rollback_session.add_all(
            [
                PriceHistory(
                    asset_id=asset.id,
                    date=day,
                    close=close,
                    currency="EUR",
                    source_plugin_key="signal_test",
                )
                for day, close in closes.items()
            ]
        )
        await asset_signal_rollback_session.flush()
        return asset.id

    return create


async def seven_day_signals(session, asset_id: int, signals: list[SignalRequest]):
    results = await AssetSourceManager.get_prices_bulk(
        [
            FAPriceQueryItem(
                asset_id=asset_id,
                date_range=SEVEN_DAY_VISIBLE,
                include_price=False,
                signals=signals,
            )
        ],
        session,
    )
    return result_for_asset(results, asset_id)


def seven_day_sma() -> list[SignalRequest]:
    return [SignalRequest(instance_id="sma", signal_code="SMA", params={"period": SEVEN_DAY_SMA_PERIOD})]


def loaded_days(closes: dict[date, Decimal], coverage) -> list[date]:
    """The calendar days the adapter loaded, read from the coverage it reports."""
    return [day for day in closes if coverage.first_available_date <= day <= coverage.last_available_date]


def assert_is_the_sma_of(series, quotes: dict[date, Decimal]) -> None:
    """Dated on the visible quote days, valued as the SMA of the quotes alone."""
    days = sorted(quotes)
    closes = [float(quotes[day]) for day in days]
    period = SEVEN_DAY_SMA_PERIOD
    expected = {day: sum(closes[index + 1 - period : index + 1]) / period for index, day in enumerate(days) if index + 1 >= period}
    assert [point.date for point in series.points] == [day for day in days if SEVEN_DAY_VISIBLE.start <= day <= SEVEN_DAY_VISIBLE.end]
    for point in series.points:
        if point.date in expected:
            assert point.value == pytest.approx(expected[point.date]), point.date.isoformat()
        else:
            assert point.value is None, point.date.isoformat()


@pytest.mark.asyncio
async def test_stored_weekend_carries_reach_the_signals_backfilled(
    asset_signal_rollback_session,
    seven_day_asset,
    served_market_holidays,
):
    """T5 — justETF stores Saturday and Sunday as Friday's close: two carries, not two quotes."""
    closes = seven_day_closes()
    asset_id = await seven_day_asset(closes)

    signal = (await seven_day_signals(asset_signal_rollback_session, asset_id, seven_day_sma())).signals[0]

    coverage = signal.availability.input_coverage
    loaded = loaded_days(closes, coverage)
    weekdays = [day for day in loaded if day.weekday() < 5]
    # Premise: the loaded span is calendar-complete and opens on a quote.
    assert coverage.first_available_date.weekday() < 5
    assert coverage.last_available_date == SEVEN_DAY_VISIBLE.end
    assert (coverage.available_points, coverage.missing_points) == (len(loaded), 0)
    # Coverage keeps the calendar; its split now reads the weekend rows as carried.
    assert (coverage.observed_points, coverage.backfilled_points) == (len(weekdays), len(loaded) - len(weekdays))
    assert_is_the_sma_of(signal.series[0], {day: closes[day] for day in weekdays})


@pytest.mark.asyncio
async def test_a_weekend_row_that_moves_stays_a_quote(
    asset_signal_rollback_session,
    seven_day_asset,
    served_market_holidays,
):
    """T5 — weekend *and* exact repeat: a Saturday that moves is a quote, its Sunday repeat is not."""
    closes = seven_day_closes(moving_saturdays=frozenset({MOVING_SATURDAY}))
    asset_id = await seven_day_asset(closes)

    signal = (await seven_day_signals(asset_signal_rollback_session, asset_id, seven_day_sma())).signals[0]

    coverage = signal.availability.input_coverage
    loaded = loaded_days(closes, coverage)
    quotes = {day: closes[day] for day in loaded if day.weekday() < 5 or day == MOVING_SATURDAY}
    dates = [point.date for point in signal.series[0].points]
    assert MOVING_SATURDAY in dates
    assert MOVING_SATURDAY + timedelta(days=1) not in dates
    assert (coverage.observed_points, coverage.backfilled_points) == (len(quotes), len(loaded) - len(quotes))
    assert_is_the_sma_of(signal.series[0], quotes)


@pytest.mark.asyncio
async def test_the_served_holiday_table_marks_a_holiday_repeat_but_not_a_move_or_a_flat_weekday(
    asset_signal_rollback_session,
    seven_day_asset,
    served_market_holidays,
):
    """T5 — the union-holiday table extends the rule to weekdays: only an exact repeat on a
    listed day is a carry; a listed day that moves and an unlisted flat weekday stay quotes."""
    served_market_holidays.table = frozenset({TABLE_DAY_THAT_MOVES, TABLE_DAY_THAT_REPEATS})
    closes = seven_day_closes(repeating_weekdays=frozenset({TABLE_DAY_THAT_REPEATS, FLAT_WEEKDAY}))
    asset_id = await seven_day_asset(closes)

    signal = (await seven_day_signals(asset_signal_rollback_session, asset_id, seven_day_sma())).signals[0]

    coverage = signal.availability.input_coverage
    loaded = loaded_days(closes, coverage)
    quotes = {day: closes[day] for day in loaded if day.weekday() < 5 and day != TABLE_DAY_THAT_REPEATS}
    dates = [point.date for point in signal.series[0].points]
    assert TABLE_DAY_THAT_REPEATS not in dates
    assert TABLE_DAY_THAT_MOVES in dates
    assert FLAT_WEEKDAY in dates
    assert (coverage.observed_points, coverage.backfilled_points) == (len(quotes), len(loaded) - len(quotes))
    assert_is_the_sma_of(signal.series[0], quotes)
    assert served_market_holidays.awaits == 1


@pytest.mark.asyncio
async def test_calendar_return_reports_a_stored_weekend_carry_as_carried(
    asset_signal_rollback_session,
    seven_day_asset,
    served_market_holidays,
):
    """T5 — the calendar return reads the same calendar days and values; the carries it reads
    are now reported as carried from Friday, because they reach the service marked."""
    closes = seven_day_closes()
    asset_id = await seven_day_asset(closes)

    signal = (
        await seven_day_signals(
            asset_signal_rollback_session,
            asset_id,
            [SignalRequest(instance_id="calendar", signal_code=CALENDAR_SIGNAL_CODE, params={"window_days": 7})],
        )
    ).signals[0]

    assert signal.status == SignalStatus.OK
    series = calendar_series(signal)
    assert [point.date for point in series.points] == [SEVEN_DAY_VISIBLE.start + timedelta(days=offset) for offset in range(28)]
    for point in series.points:
        assert point.value == pytest.approx((float(closes[point.date]) / float(closes[point.date - timedelta(days=7)]) - 1) * 100)
    saturday = point_on(series, date(2024, 3, 16))
    assert (saturday.provenance.current_price_date, saturday.provenance.current_price_days_back) == (date(2024, 3, 15), 1)
    assert (saturday.provenance.reference_price_date, saturday.provenance.reference_price_days_back) == (date(2024, 3, 8), 1)


@pytest.mark.asyncio
async def test_one_bulk_call_awaits_the_holiday_table_once_and_hands_it_to_both_prepared_sets(
    monkeypatch,
    asset_signal_data,
    served_market_holidays,
):
    """T5 — one await per call, whatever the number of requests, and the same table for the
    primary prepared set and for the primary-with-comparison set."""
    served_market_holidays.table = frozenset({date(1899, 12, 31)})  # a date nothing here is quoted near
    prepared_with: list[object] = []
    real_prepare = price_query_module.prepare_asset_series_set

    def prepare_spy(*args, **kwargs):
        prepared_with.append(kwargs.get("market_holidays", NOT_PASSED))
        return real_prepare(*args, **kwargs)

    monkeypatch.setattr(price_query_module, "prepare_asset_series_set", prepare_spy)
    primary_id, comparison_id = asset_signal_data["asset_ids"][:2]
    async with AsyncSession(
        get_async_engine(),
        expire_on_commit=False,
    ) as session:
        results = await AssetSourceManager.get_prices_bulk(
            [
                FAPriceQueryItem(
                    asset_id=primary_id,
                    date_range=visible_range(asset_signal_data),
                    include_price=False,
                    signals=[
                        SignalRequest(instance_id="sma", signal_code="SMA", params={"period": 5}),
                        SignalRequest(
                            instance_id="beta",
                            signal_code="RISK_ROLLING_BETA",
                            params={"window": 10, "comparison_asset_id": comparison_id},
                        ),
                    ],
                ),
                FAPriceQueryItem(
                    asset_id=comparison_id,
                    date_range=visible_range(asset_signal_data),
                    include_price=False,
                    signals=[SignalRequest(instance_id="ema", signal_code="EMA", params={"period": 14})],
                ),
            ],
            session,
        )

    assert [signal.status for result in results for signal in result.signals] == [SignalStatus.OK] * 3
    # Premise: the beta prepares the primary set, then the primary-with-comparison set.
    assert len(prepared_with) == 2
    assert served_market_holidays.awaits == 1
    assert prepared_with == [served_market_holidays.table, served_market_holidays.table]


@pytest.mark.asyncio
async def test_a_bulk_call_without_signals_never_awaits_the_holiday_table(
    asset_signal_data,
    served_market_holidays,
):
    """Only a computation reads the table: a plain price query must not wait for its build."""
    asset_id = asset_signal_data["primary_asset_id"]
    async with AsyncSession(
        get_async_engine(),
        expire_on_commit=False,
    ) as session:
        results = await AssetSourceManager.get_prices_bulk(
            [FAPriceQueryItem(asset_id=asset_id, date_range=visible_range(asset_signal_data))],
            session,
        )

    assert len(result_for_asset(results, asset_id).prices) == 30  # premise: the prices were served
    assert served_market_holidays.awaits == 0


def spy_load_starts(monkeypatch) -> list[date]:
    """Record the first calendar day of every price series the adapter builds."""
    starts: list[date] = []
    real = PriceQueryOperations._build_backward_filled_series

    def spy(price_map, start_date, end_date, seed_price=None):
        starts.append(start_date)
        return real(price_map, start_date, end_date, seed_price=seed_price)

    monkeypatch.setattr(PriceQueryOperations, "_build_backward_filled_series", staticmethod(spy))
    return starts


async def signals_on_primary(asset_signal_data, signals: list[SignalRequest]):
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
                    signals=signals,
                )
            ],
            session,
        )
    return result_for_asset(results, asset_id)


def plugin_total_points(signal_code: str, params: dict) -> int:
    plugin_class = SignalPluginRegistry.get_plugin(signal_code)
    context = SignalExecutionContext(
        domain=SignalDomain.ASSET,
        requested_range=DateRangeModel(start=date(2026, 1, 1)),
        source_reference="asset:warmup",
    )
    return plugin_class.warmup_requirement(plugin_class.validate_params(params), context).total_points


@pytest.mark.asyncio
async def test_sma_200_loads_400_calendar_days_before_the_visible_start(
    monkeypatch,
    asset_signal_data,
    served_market_holidays,
):
    """T6 — «SMA 200 = 200 sedute»: two calendar days per session of warm-up."""
    starts = spy_load_starts(monkeypatch)
    requested = visible_range(asset_signal_data)

    signal = (await signals_on_primary(asset_signal_data, [SignalRequest(instance_id="sma", signal_code="SMA", params={"period": 200})])).signals[0]

    assert starts == [requested.start - timedelta(days=400)]
    # Every calendar day of this fixture is a quote: the 400 days are 400 sessions.
    assert signal.status == SignalStatus.OK
    assert (signal.warmup.loaded_points, signal.warmup.used_points) == (430, 400)


@pytest.mark.asyncio
async def test_a_full_history_plan_still_loads_from_the_first_price(
    monkeypatch,
    asset_signal_data,
    served_market_holidays,
):
    """T6 — guard: a full-history plan (drawdown) keeps loading the whole history."""
    starts = spy_load_starts(monkeypatch)

    result = await signals_on_primary(
        asset_signal_data,
        [
            SignalRequest(instance_id="sma", signal_code="SMA", params={"period": 200}),
            SignalRequest(instance_id="drawdown", signal_code="RISK_DRAWDOWN", params={}),
        ],
    )

    assert starts == [date.min]
    sma = next(signal for signal in result.signals if signal.instance_id == "sma")
    assert sma.warmup.loaded_points == 500  # the whole fixture: nothing precedes its first row


@pytest.mark.asyncio
async def test_a_prepared_risk_signal_keeps_its_own_multiplier(
    monkeypatch,
    asset_signal_data,
    served_market_holidays,
):
    """T6 — guard: the prepared risk signals already load twice their points."""
    starts = spy_load_starts(monkeypatch)
    requested = visible_range(asset_signal_data)

    await signals_on_primary(
        asset_signal_data,
        [SignalRequest(instance_id="volatility", signal_code="RISK_ROLLING_VOLATILITY", params={"window": 20})],
    )

    assert starts == [requested.start - timedelta(days=2 * plugin_total_points("RISK_ROLLING_VOLATILITY", {"window": 20}))]


@pytest.mark.asyncio
async def test_calendar_return_keeps_a_calendar_day_load_window(
    monkeypatch,
    asset_signal_data,
    served_market_holidays,
):
    """T6 — guard: the calendar return is no session plugin; its window is calendar days."""
    starts = spy_load_starts(monkeypatch)
    requested = visible_range(asset_signal_data)

    await signals_on_primary(
        asset_signal_data,
        [SignalRequest(instance_id="calendar", signal_code=CALENDAR_SIGNAL_CODE, params={"window_days": 30})],
    )

    assert starts == [requested.start - timedelta(days=30)]
