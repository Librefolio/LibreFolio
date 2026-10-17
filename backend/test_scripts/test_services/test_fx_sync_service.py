"""
FX sync service tests.

Focus: pair-sync orchestration branches in services/fx/sync.py
- _is_date_within_sync_range
- sync_pairs_bulk._process_route
- sync_pairs_bulk._compute_multi_step
- X-R38: a rate no column can keep, in sync_pairs_bulk and ensure_rates_multi_source (see its block at the end)
- X-R50 (E's review R13-SEC5 on X-R38): a rate whose double is 1E+14, in sync_pairs_bulk (in the X-R38 block)
- X-R65 (N83): no provider rate stored before 1900-01-01, whatever the start ("min" included), in
  _is_date_within_sync_range and sync_pairs_bulk (its block at the end)
"""

import asyncio
import json
import sys
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, Mock

import pytest
from structlog.testing import capture_logs

from backend.app.config import PROJECT_ROOT

sys.path.insert(0, str(PROJECT_ROOT))

from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import delete, select

from backend.app.db.models import FxConversionRoute, FxRate
from backend.app.db.session import get_async_engine
from backend.app.schemas.refresh import SyncStatus
from backend.app.services.fx import runtime as fx_runtime
from backend.app.services.fx import sync as fx_service
from backend.app.services.fx.sync import _is_date_within_sync_range, ensure_rates_multi_source, sync_pairs_bulk
from backend.app.services.fx_providers.mockfx.plugin import MOCKFX_FIXED_RATE, MockFXProvider
from backend.test_scripts.test_utils import print_section, print_success

# The two pairs this file works on, and the only rows it is entitled to remove.
#
# The fixture below used to be two DELETEs with no WHERE, committed: it emptied the
# whole `fx_rates` table *and every FX route in the database* before each of its
# tests. That took the mock's ECB series and every route another test had just
# configured with it, and a committed DELETE is not something a neighbour's rollback
# can put back.
#
# Scoping the rates by MOCKFX is enough because that provider only ever runs in
# tests: a real ECB or SNB row is never touched. The routes are scoped by pair.
FX_SYNC_PAIRS = (("EUR", "USD"), ("GBP", "JPY"))


@pytest.fixture(autouse=True)
def _clean_fx_tables():
    """Remove this file's own rates and routes, and nobody else's."""

    async def _purge():
        engine = get_async_engine()
        async with AsyncSession(engine) as session:
            await session.execute(delete(FxRate).where(FxRate.source == "MOCKFX"))
            for base, quote in FX_SYNC_PAIRS:
                await session.execute(delete(FxConversionRoute).where(FxConversionRoute.base == base, FxConversionRoute.quote == quote))
            await session.commit()

    asyncio.run(_purge())
    yield


class TestFXSyncHelpers:
    """Pure helper coverage for sync-range logic."""

    def test_is_date_within_sync_range_supports_min_and_explicit_start(self):
        """Cover both 'min' and explicit-date branches."""
        print_section("_is_date_within_sync_range")

        assert _is_date_within_sync_range(date(1900, 1, 1), "min", date(1900, 1, 3)) is True
        assert _is_date_within_sync_range(date(1900, 1, 4), "min", date(1900, 1, 3)) is False

        assert _is_date_within_sync_range(date(2025, 1, 2), date(2025, 1, 2), date(2025, 1, 3)) is True
        assert _is_date_within_sync_range(date(2025, 1, 1), date(2025, 1, 2), date(2025, 1, 3)) is False

        print_success("Covered min + explicit-date range branches")


@pytest.mark.asyncio
class TestSyncPairsBulk:
    """Deterministic sync_pairs_bulk coverage with mock providers."""

    async def test_sync_pairs_bulk_single_step_direct_route(self):
        """Single-step MOCKFX route should use direct _process_route branch."""
        print_section("sync_pairs_bulk: single-step direct route")

        engine = get_async_engine()
        start_date = date(2025, 1, 1)
        end_date = date(2025, 1, 2)

        async with AsyncSession(engine, expire_on_commit=False) as session:
            session.add(
                FxConversionRoute(
                    base="EUR",
                    quote="USD",
                    priority=1,
                    chain_steps=json.dumps(
                        [
                            {"from": "EUR", "to": "USD", "provider": "MOCKFX"},
                        ]
                    ),
                )
            )
            await session.commit()

            response = await sync_pairs_bulk(
                session,
                pairs=["EUR-USD"],
                date_range=(start_date, end_date),
            )

        result = response.results[0]
        assert result.status == "ok"
        assert result.provider_used == "MOCKFX"
        assert result.points_fetched == 2
        assert result.points_changed == 2

        async with AsyncSession(engine) as verify_session:
            # Filtered by source as well as pair: counting every EUR/USD row in the
            # table was a global count this test never created, and it only ever
            # worked because the fixture had just emptied the table for everyone.
            rows = (await verify_session.execute(select(FxRate).where(FxRate.base == "EUR", FxRate.quote == "USD", FxRate.source == "MOCKFX").order_by(FxRate.date))).scalars().all()

        assert len(rows) == 2
        assert all(row.rate == MOCKFX_FIXED_RATE for row in rows)
        assert all(row.source == "MOCKFX" for row in rows)
        print_success("Single-step route persisted direct MOCKFX rates")

    async def test_sync_pairs_bulk_multi_step_chain_with_min_start(self):
        """Multi-step MOCKFX chain should persist composite rates for 'min' range."""
        print_section("sync_pairs_bulk: multi-step chain with start='min'")

        engine = get_async_engine()
        end_date = date(1900, 1, 3)

        async with AsyncSession(engine, expire_on_commit=False) as session:
            session.add(
                FxConversionRoute(
                    base="GBP",
                    quote="JPY",
                    priority=1,
                    chain_steps=json.dumps(
                        [
                            {"from": "GBP", "to": "EUR", "provider": "MOCKFX"},
                            {"from": "EUR", "to": "JPY", "provider": "MOCKFX"},
                        ]
                    ),
                )
            )
            await session.commit()

            response = await sync_pairs_bulk(
                session,
                pairs=["GBP-JPY"],
                date_range=("min", end_date),
            )

        assert response.success_count == 1
        assert response.total_points_changed == 3
        assert len(response.results) == 1

        result = response.results[0]
        assert result.pair == "GBP-JPY"
        assert result.status == "ok"
        assert result.provider_used == "CHAIN:MOCKFX+MOCKFX"
        assert result.points_fetched == 3
        assert result.points_changed == 3
        assert result.errors == []
        assert result.detail is not None
        assert len(result.detail) == 2
        assert all(item.dates_available == 3 for item in result.detail)

        async with AsyncSession(engine) as verify_session:
            rows = (await verify_session.execute(select(FxRate).where(FxRate.base == "GBP", FxRate.quote == "JPY").order_by(FxRate.date))).scalars().all()

        assert len(rows) == 3
        assert all(row.source == "CHAIN:MOCKFX+MOCKFX" for row in rows)
        assert all(row.rate == Decimal("1") for row in rows)
        assert MOCKFX_FIXED_RATE == Decimal("1.234500")

        print_success("Multi-step chain persisted 3 composite GBP/JPY rates")

    async def test_sync_pairs_bulk_repeated_provider_cache_hit_preserves_source_and_steps(self, monkeypatch):
        """A deterministic fetch-cache hit must not shorten the configured chain."""
        engine = get_async_engine()
        start_date, end_date = date(1900, 1, 5), date(1900, 1, 6)
        steps = [
            {"from": "GBP", "to": "EUR", "provider": "MOCKFX"},
            {"from": "EUR", "to": "JPY", "provider": "MOCKFX"},
        ]
        route = FxConversionRoute(base="GBP", quote="JPY", priority=1, chain_steps=json.dumps(steps))
        owned_rate_scope = (
            FxRate.base == "GBP",
            FxRate.quote == "JPY",
            FxRate.date >= start_date,
            FxRate.date <= end_date,
        )
        async with AsyncSession(engine) as check_session:
            existing = (await check_session.execute(select(FxRate).where(*owned_rate_scope))).scalars().all()
            assert existing == [], "Cache regression requires unused pair/dates; do not overwrite existing rates"

        # Test only the hit/miss contract, not TTL timing or the shared cache.
        cached_values = {}
        cache = Mock()
        cache.get.side_effect = lambda key: (cached_values.get(key), key in cached_values)
        cache.set.side_effect = lambda key, value: cached_values.__setitem__(key, value)
        monkeypatch.setattr(fx_service, "_fx_fetch_cache", cache)
        provider = MockFXProvider()
        fetch = AsyncMock(wraps=provider.fetch_rates)
        monkeypatch.setattr(provider, "fetch_rates", fetch)

        def get_provider(code):
            assert code == "MOCKFX", "This regression must never instantiate a live bank provider"
            return provider

        monkeypatch.setattr(fx_service.FXProviderRegistry, "get_provider_instance", get_provider)
        # Provider, currencies and range; since CP10 a 4th element closes the key, the provider's settings fingerprint
        # (fx/runtime.settings_cache_part). It is built after each sync: ``provider`` is the very object
        # configure_instance binds, since the patched lookup hands it out.
        cache_key = ("MOCKFX", frozenset({"GBP", "JPY"}), (start_date, end_date))

        try:
            async with AsyncSession(engine, expire_on_commit=False) as session:
                session.add(route)
                await session.commit()

                for expected_changes in (2, 0):
                    response = await sync_pairs_bulk(session, pairs=["GBP-JPY"], date_range=(start_date, end_date))
                    full_key = cache_key + (fx_runtime.settings_cache_part(provider),)
                    assert full_key[3], "MOCKFX declares settings: the key's 4th element is their fingerprint, never empty"
                    result = next(item for item in response.results if item.pair == "GBP-JPY")
                    assert response.success_count == 1
                    assert response.total_points_changed == expected_changes
                    assert result.status == "ok"
                    assert result.provider_used == "CHAIN:MOCKFX+MOCKFX"
                    assert result.points_fetched == 2
                    assert result.points_changed == expected_changes
                    assert result.errors == []
                    assert result.detail is not None
                    assert [(leg.provider, leg.leg, leg.dates_available, leg.error) for leg in result.detail] == [
                        ("MOCKFX", "GBP→EUR", 2, None),
                        ("MOCKFX", "EUR→JPY", 2, None),
                    ]
                    assert {"is_chain", "providers_used"}.isdisjoint(result.model_dump())
                    fetch.assert_awaited_once()
                    assert full_key in cached_values

                    async with AsyncSession(engine) as verify_session:
                        stored = (await verify_session.execute(select(FxConversionRoute).where(FxConversionRoute.id == route.id))).scalar_one()
                        assert stored.parsed_steps == steps
                        rows = (await verify_session.execute(select(FxRate).where(*owned_rate_scope))).scalars().all()
                        assert {row.date: (row.source, row.rate) for row in rows} == {
                            start_date: ("CHAIN:MOCKFX+MOCKFX", Decimal("1")),
                            end_date: ("CHAIN:MOCKFX+MOCKFX", Decimal("1")),
                        }

            assert cache.get.call_count == 2
            assert all(call.args == (full_key,) for call in cache.get.call_args_list)
            cache.set.assert_called_once()
            assert fetch.await_args.args[0] == (start_date, end_date)
            assert set(fetch.await_args.args[1]) == {"GBP", "JPY"}
        finally:
            # Exclusivity remains required. The preflight proved these exact
            # pair/dates were empty; cleanup must also work if a source is wrong.
            async with AsyncSession(engine) as cleanup_session:
                await cleanup_session.execute(delete(FxRate).where(*owned_rate_scope))
                if route.id is not None:
                    await cleanup_session.execute(delete(FxConversionRoute).where(FxConversionRoute.id == route.id))
                await cleanup_session.commit()

    async def test_sync_pairs_bulk_manual_skips_fetch_and_has_no_route_metadata(self, monkeypatch):
        """MANUAL membership does not become sync provenance or fetched data."""
        engine = get_async_engine()
        target_date = date(1900, 1, 7)
        route = FxConversionRoute(
            base="EUR",
            quote="USD",
            priority=999,
            chain_steps=json.dumps([{"from": "EUR", "to": "USD", "provider": "MANUAL"}]),
        )
        rate_scope = (FxRate.base == "EUR", FxRate.quote == "USD", FxRate.date == target_date)
        async with AsyncSession(engine) as check_session:
            existing = (await check_session.execute(select(FxRate).where(*rate_scope))).scalars().all()
            assert existing == [], "MANUAL regression requires an unused date; do not overwrite existing rates"

        lookup = Mock(side_effect=AssertionError("MANUAL-only sync must not instantiate a provider"))
        cache = Mock()
        cache.get.side_effect = AssertionError("MANUAL-only sync must not access the fetch cache")
        monkeypatch.setattr(fx_service.FXProviderRegistry, "get_provider_instance", lookup)
        monkeypatch.setattr(fx_service, "_fx_fetch_cache", cache)

        try:
            async with AsyncSession(engine, expire_on_commit=False) as session:
                session.add(route)
                await session.commit()
                response = await sync_pairs_bulk(session, pairs=["EUR-USD"], date_range=(target_date, target_date))

            result = next(item for item in response.results if item.pair == "EUR-USD")
            assert response.success_count == 1
            assert response.total_points_changed == 0
            assert result.status == "skipped"
            assert result.provider_used is None
            assert result.points_fetched == 0
            assert result.points_changed == 0
            assert result.errors == []
            assert {"is_chain", "providers_used"}.isdisjoint(result.model_dump())
            lookup.assert_not_called()
            cache.get.assert_not_called()
            cache.set.assert_not_called()
            async with AsyncSession(engine) as verify_session:
                rows = (await verify_session.execute(select(FxRate).where(*rate_scope))).scalars().all()
                assert rows == []
        finally:
            async with AsyncSession(engine) as cleanup_session:
                # Normally there are no rates; remove only this proven-empty
                # pair/date if a regression unexpectedly wrote one.
                await cleanup_session.execute(delete(FxRate).where(*rate_scope))
                if route.id is not None:
                    await cleanup_session.execute(delete(FxConversionRoute).where(FxConversionRoute.id == route.id))
                await cleanup_session.commit()


# ============================================================================
# X-R38 (the FX side of W-B58): a rate no column can keep, in the provider sync
# ============================================================================
#
# Measured before the cure. A provider's rate reaches fx_rates through truncate_fx_rate (sync_pairs_bulk: one step and
# chains; the unwired ensure_rates_multi_source: twice) and is compared with the stored one through it
# (_count_actual_changes; ensure_rates_multi_source). truncate_fx_rate raises InvalidOperation from 1E+50 up and on
# Infinity: the route of the pair fails and none of its dates is stored (ensure_rates_multi_source raises). Below that,
# 1E+15 is stored as it is and 1E-11 as 0; a NaN fails the NOT NULL of the column; the inverse of 0 (BIF/EUR, quoted
# EUR → BIF) raises DivisionByZero while the provider's answer is read, and every leg of that provider fails. A legacy
# stored inf or 1e60 makes the comparison raise the same way.
#
# Contract (X-R38): an observation, or a chain rate, that storable_fx_rate refuses is skipped, never stored and never
# raising, and logged once per sync: one warning naming the pair for all its skipped dates. Every other observation of
# the same sync is stored. A legacy stored rate no column can keep compares as a change, so the new rate overwrites it.
#
# X-R50 (E's review R13-SEC5 on X-R38), measured before its cure: 99999999999999.995 has the 14 digits before the decimal
# point X-R38 lets through, so storable_fx_rate keeps it and the sync stores it; SQLite keeps it as its double, 1E+14,
# which every conversion skips (convert_bulk reads only 1E-10 <= rate < 1E+14). Contract (X-R50): a rate whose double is
# 1E+14 or more is one no column can keep, skipped and logged as above.
#
# The pairs are this block's own (no seed and no other test uses UGX, BIF, RWF or TZS): their rates in the window and
# their routes are wiped before and after each test. The provider is the file's MOCKFX double, a MockFXProvider whose
# fetch answers the test's rates, behind a fetch cache of the test's own.

XR38_DAYS = tuple(date(1990, 3, 5) + timedelta(days=offset) for offset in range(5))
#: MOCKFX quotes EUR → UGX: stored EUR/UGX, as it comes.
XR38_DIRECT = ("EUR", "UGX")
#: MOCKFX quotes EUR → BIF: stored BIF/EUR, its inverse.
XR38_INVERTED = ("BIF", "EUR")
#: RWF → EUR → TZS, two MOCKFX legs: only the chain rate is stored, as RWF/TZS.
XR38_CHAIN = ("RWF", "TZS")
#: What a pair is delivered on days 0, 2 and 4, around the rate under test (days 1 and 3), and what those days store.
_XR38_AROUND = {
    XR38_DIRECT: (("1.5", "2.5", "3.5"), (Decimal("1.5"), Decimal("2.5"), Decimal("3.5"))),
    XR38_INVERTED: (("2", "4", "8"), (Decimal("0.5"), Decimal("0.25"), Decimal("0.125"))),
}
_XR38_BARRIER = "X-R38 capture barrier"
_XR38_LEGACY = [
    pytest.param(float("inf"), id="inf"),
    pytest.param(0.0, id="0"),
    pytest.param(1e19, id="1e19-20-integer-digits"),
    pytest.param(1e60, id="1e60"),
]


def _xr38_quoted(pair: tuple[str, str]) -> str:
    """The currency MOCKFX quotes against EUR for the pair."""
    return pair[1] if pair[0] == "EUR" else pair[0]


def _xr38_around(pair: tuple[str, str], delivered: str) -> tuple[list[str], dict[date, Decimal]]:
    """The pair's five deliveries, ``delivered`` on days 1 and 3, and what days 0, 2 and 4 store."""
    sent, kept = _XR38_AROUND[pair]
    return [sent[0], delivered, sent[1], delivered, sent[2]], {XR38_DAYS[0]: kept[0], XR38_DAYS[2]: kept[1], XR38_DAYS[4]: kept[2]}


async def _xr38_wipe() -> None:
    """Drop this block's rates in the window, and its routes."""
    async with AsyncSession(get_async_engine()) as session:
        for base, quote in (XR38_DIRECT, XR38_INVERTED, XR38_CHAIN):
            await session.execute(delete(FxRate).where(FxRate.base == base, FxRate.quote == quote, FxRate.date >= XR38_DAYS[0], FxRate.date <= XR38_DAYS[-1]))
            await session.execute(delete(FxConversionRoute).where(FxConversionRoute.base == base, FxConversionRoute.quote == quote))
        await session.commit()


@pytest.fixture
def xr38_pairs():
    """X-R38: this block's pairs without a rate in the window nor a route, before and after the test."""
    asyncio.run(_xr38_wipe())
    yield
    asyncio.run(_xr38_wipe())


def _xr38_provider(monkeypatch: pytest.MonkeyPatch, rates: dict[str, list[str | None]]) -> None:
    """MOCKFX handed out as a MockFXProvider whose fetch answers, for each currency asked, ``rates[currency]``: one rate per
    ``XR38_DAYS`` day (None: no observation that day), quoted EUR → currency as MOCKFX quotes. The fetch cache is the
    test's own, so that an earlier fetch of the same range cannot answer instead of the double."""
    provider = MockFXProvider()

    async def fetch_rates(date_range, currencies, base_currency=None):
        return {currency: [(day, "EUR", currency, Decimal(rate)) for day, rate in zip(XR38_DAYS, rates[currency], strict=True) if rate is not None] for currency in currencies}

    def get_provider(code):
        return provider if code == "MOCKFX" else None

    cached = {}
    cache = Mock()
    cache.get.side_effect = lambda key: (cached.get(key), key in cached)
    cache.set.side_effect = cached.__setitem__
    monkeypatch.setattr(provider, "fetch_rates", fetch_rates)
    monkeypatch.setattr(fx_service.FXProviderRegistry, "get_provider_instance", get_provider)
    monkeypatch.setattr(fx_service, "_fx_fetch_cache", cache)


async def _xr38_route(base: str, quote: str, steps: list[tuple[str, str]]) -> None:
    """The pair's route, one MOCKFX step per (from, to)."""
    async with AsyncSession(get_async_engine()) as session:
        session.add(FxConversionRoute(base=base, quote=quote, priority=1, chain_steps=json.dumps([{"from": source, "to": target, "provider": "MOCKFX"} for source, target in steps])))
        await session.commit()


async def _xr38_plant(base: str, quote: str, day: date, rate: float) -> None:
    """A legacy rate as an older release could leave it, written with raw SQL past the model, and committed."""
    key = {"day": day.isoformat(), "base": base, "quote": quote}
    async with AsyncSession(get_async_engine()) as session:
        await session.execute(text("INSERT INTO fx_rates (date, base, quote, rate, source, fetched_at) VALUES (:day, :base, :quote, :rate, 'LEGACY', CURRENT_TIMESTAMP)"), {**key, "rate": rate})
        await session.commit()
        found = (await session.execute(text("SELECT rate FROM fx_rates WHERE base = :base AND quote = :quote AND date = :day"), key)).scalar_one()
    assert found == rate, f"barrier: the legacy rate reads back {found!r} with raw SQL, not {rate!r}"


async def _xr38_stored(base: str, quote: str) -> dict[date, Decimal]:
    """The pair's rates in the window by date, read through the model, as the app reads them."""
    async with AsyncSession(get_async_engine()) as session:
        rows = (await session.execute(select(FxRate.date, FxRate.rate).where(FxRate.base == base, FxRate.quote == quote, FxRate.date >= XR38_DAYS[0], FxRate.date <= XR38_DAYS[-1]))).all()
    return {row.date: row.rate for row in rows}


def _xr38_warnings(events: list[dict], *codes: str) -> list[dict]:
    """The warnings, and worse, among ``events`` that name every one of ``codes``; the barrier left out."""
    return [event for event in events if event.get("log_level") in ("warning", "error", "critical") and event.get("event") != _XR38_BARRIER and all(code in str(event) for code in codes)]


def _xr38_assert_the_capture_saw(events: list[dict]) -> None:
    """Barrier: an event sent through sync.py's own logger inside the capture is there, so a missing warning is a warning
    not logged, never a blind capture."""
    assert any(event.get("event") == _XR38_BARRIER for event in events), f"barrier: the log capture saw no event of sync.py's logger: {events}"


async def _xr38_sync(base: str, quote: str, story: str):
    """``sync_pairs_bulk`` of the pair over ``XR38_DAYS``, its log events captured: (the pair's result, the events). An
    exception fails the test, naming it."""
    slug = f"{base}-{quote}"
    with capture_logs() as events:
        fx_service.logger.warning(_XR38_BARRIER)
        try:
            async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
                response = await sync_pairs_bulk(session, pairs=[slug], date_range=(XR38_DAYS[0], XR38_DAYS[-1]))
        except Exception as exc:  # noqa: BLE001 — any exception is the defect under test
            pytest.fail(f"{story}: sync_pairs_bulk raised {exc!r} (X-R38: never raising)")
    _xr38_assert_the_capture_saw(events)
    return next(item for item in response.results if item.pair == slug), events


async def _xr38_ensure(currency: str, story: str):
    """``ensure_rates_multi_source`` of MOCKFX for ``currency`` over ``XR38_DAYS``, its log events captured: (its summary,
    the events). An exception fails the test, naming it."""
    with capture_logs() as events:
        fx_service.logger.warning(_XR38_BARRIER)
        try:
            async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
                summary = await ensure_rates_multi_source(session, (XR38_DAYS[0], XR38_DAYS[-1]), [currency], provider_code="MOCKFX")
        except Exception as exc:  # noqa: BLE001 — any exception is the defect under test
            pytest.fail(f"{story}: ensure_rates_multi_source raised {exc!r} (X-R38: never raising)")
    _xr38_assert_the_capture_saw(events)
    return summary, events


@pytest.mark.asyncio
@pytest.mark.usefixtures("xr38_pairs")
@pytest.mark.parametrize(
    ("pair", "delivered"),
    [
        pytest.param(XR38_DIRECT, "1E+15", id="EUR-UGX-1E+15"),
        pytest.param(XR38_DIRECT, "100000000000000", id="EUR-UGX-15-integer-digits"),
        pytest.param(XR38_DIRECT, "1E+50", id="EUR-UGX-1E+50"),
        pytest.param(XR38_DIRECT, "1E+400", id="EUR-UGX-1E+400"),
        pytest.param(XR38_DIRECT, "Infinity", id="EUR-UGX-Infinity"),
        pytest.param(XR38_DIRECT, "NaN", id="EUR-UGX-NaN"),
        pytest.param(XR38_DIRECT, "1E-11", id="EUR-UGX-1E-11"),
        pytest.param(XR38_DIRECT, "0", id="EUR-UGX-0"),
        pytest.param(XR38_INVERTED, "1E-15", id="BIF-EUR-1E-15-inverse-1E+15"),
        pytest.param(XR38_INVERTED, "1E+11", id="BIF-EUR-1E+11-inverse-1E-11"),
        pytest.param(XR38_INVERTED, "0", id="BIF-EUR-0-no-inverse"),
        pytest.param(XR38_INVERTED, "1E-1000000", id="derived-BIF-EUR-1E-1000000-the-inverse-overflows"),
    ],
)
async def test_xr38_sync_skips_a_rate_no_column_can_keep_and_stores_the_others(monkeypatch, pair, delivered):
    """Red today. EUR/UGX: 1E+15 and 15 integer digits are stored as they are, 1E-11 and 0 as 0; from 1E+50, on Infinity
    and on NaN (the NOT NULL of the column) the route fails and none of the five days is stored. BIF/EUR, quoted EUR → BIF
    and stored inverted: the inverse of 1E-15 is stored, 1E+15, the inverse of 1E+11 as 0; 0 and 1E-1000000 make the
    inversion raise while the provider's answer is read, and every leg of the provider fails.

    Contract (X-R38): days 1 and 3 are skipped; days 0, 2 and 4 are stored as delivered (inverted for BIF/EUR); the pair
    does not fail; one warning, naming the pair, for both skipped days. The ``derived-`` case reads the same rule.
    """
    base, quote = pair
    quoted = _xr38_quoted(pair)
    deliveries, expected = _xr38_around(pair, delivered)
    _xr38_provider(monkeypatch, {quoted: deliveries})
    await _xr38_route(base, quote, [(base, quote)])
    story = f"a MOCKFX sync of {base}/{quote} delivering EUR → {quoted} {delivered} on {XR38_DAYS[1]} and {XR38_DAYS[3]}"

    result, events = await _xr38_sync(base, quote, story)

    stored = await _xr38_stored(base, quote)
    assert stored == expected, f"{story} stored {stored}: expected the three other days alone, {expected} (X-R38: skip the rate no column can keep, store the others); the pair: {result.status} {result.errors}"
    assert result.status != SyncStatus.FAILED, f"{story}: the pair failed, {result.errors}"
    warnings = _xr38_warnings(events, quoted)
    assert len(warnings) == 1, f"{story} logged {len(warnings)} warning(s) naming {quoted}: expected one for both skipped days (X-R38: logged once per sync): {warnings}"


@pytest.mark.asyncio
@pytest.mark.usefixtures("xr38_pairs")
@pytest.mark.parametrize(("pair", "delivered"), [pytest.param(XR38_DIRECT, "99999999999999.995", id="EUR-UGX-double-1E+14")])
async def test_xr50_sync_skips_a_rate_whose_double_is_1E14_and_stores_the_others(monkeypatch, pair, delivered):
    """Red today: EUR → UGX 99999999999999.995 has the 14 digits before the decimal point X-R38 lets through, so days 1
    and 3 are stored, and SQLite keeps them as the double ``1E+14``: the sync reports them stored, while every conversion
    skips them as unusable (``convert_bulk`` reads only ``1E-10 <= rate < 1E+14``) and finds no rate for those days.

    Contract (X-R50), the X-R38 one for a rate no column can keep: days 1 and 3 are skipped; days 0, 2 and 4 are stored as
    delivered; the pair does not fail; one warning, naming the pair, for both skipped days.
    """
    base, quote = pair
    quoted = _xr38_quoted(pair)
    integer_digits, double = Decimal(delivered).adjusted() + 1, float(Decimal(delivered))
    assert integer_digits == 14 and double >= 1e14, f"barrier: {delivered} has {integer_digits} digits before the decimal point and the double {double!r}: expected the 14 X-R38 lets through and a double of 1E+14"
    deliveries, expected = _xr38_around(pair, delivered)
    _xr38_provider(monkeypatch, {quoted: deliveries})
    await _xr38_route(base, quote, [(base, quote)])
    story = f"a MOCKFX sync of {base}/{quote} delivering EUR → {quoted} {delivered} (its double {double!r}) on {XR38_DAYS[1]} and {XR38_DAYS[3]}"

    result, events = await _xr38_sync(base, quote, story)

    stored = await _xr38_stored(base, quote)
    assert stored == expected, f"{story} stored {stored}: expected the three other days alone, {expected} (X-R50: skip the rate whose double is 1E+14, store the others); the pair: {result.status} {result.errors}"
    assert result.status != SyncStatus.FAILED, f"{story}: the pair failed, {result.errors}"
    warnings = _xr38_warnings(events, quoted)
    assert len(warnings) == 1, f"{story} logged {len(warnings)} warning(s) naming {quoted}: expected one for both skipped days (X-R50, as X-R38: logged once per sync): {warnings}"


@pytest.mark.asyncio
@pytest.mark.usefixtures("xr38_pairs")
@pytest.mark.parametrize(
    ("rwf", "tzs", "chain"),
    [
        pytest.param("1E-10", "1E+10", "1E+20", id="chain-1E+20"),
        pytest.param("1E+6", "1E-6", "1E-12", id="chain-1E-12-0-once-truncated"),
    ],
)
async def test_xr38_sync_skips_a_chain_rate_no_column_can_keep_and_stores_the_others(monkeypatch, rwf, tzs, chain):
    """Red today: the chain rate of days 1 and 3, computed from legs each within the limits, is stored: 1E+20 as it is,
    1E-12 as 0.

    Contract (X-R38): a chain rate ``storable_fx_rate`` refuses is skipped like an observation; days 0, 2 and 4 are stored
    (RWF → EUR → TZS: 3 / 2, 10 / 4, 2 / 8); the pair does not fail; one warning, naming the pair, for both skipped days.
    """
    base, quote = XR38_CHAIN
    _xr38_provider(monkeypatch, {"RWF": ["2", rwf, "4", rwf, "8"], "TZS": ["3", tzs, "10", tzs, "2"]})
    await _xr38_route(base, quote, [("RWF", "EUR"), ("EUR", "TZS")])
    story = f"a MOCKFX chain sync of RWF/TZS (legs EUR/RWF {rwf}, EUR/TZS {tzs}) whose rate is {chain} on {XR38_DAYS[1]} and {XR38_DAYS[3]}"

    result, events = await _xr38_sync(base, quote, story)

    stored = await _xr38_stored(base, quote)
    expected = {XR38_DAYS[0]: Decimal("1.5"), XR38_DAYS[2]: Decimal("2.5"), XR38_DAYS[4]: Decimal("0.25")}
    assert stored == expected, f"{story} stored {stored}: expected the three other days alone, {expected} (X-R38: skip the chain rate no column can keep, store the others); the pair: {result.status} {result.errors}"
    assert result.status != SyncStatus.FAILED, f"{story}: the pair failed, {result.errors}"
    warnings = _xr38_warnings(events, "RWF", "TZS")
    assert len(warnings) == 1, f"{story} logged {len(warnings)} warning(s) naming RWF and TZS: expected one for both skipped days (X-R38: logged once per sync): {warnings}"


@pytest.mark.asyncio
@pytest.mark.usefixtures("xr38_pairs")
async def test_xr38_guard_sync_stores_rates_at_the_limits(monkeypatch):
    """Guard: green today and after. 14 digits before the decimal point and 1E-10 are the limits, not past them; a rate
    with more decimals is cut to 10 (0.00000000019 to 1E-10, 1.08501234567890 to 1.0850123456) and stored. Nothing is
    skipped, nothing is logged."""
    base, quote = XR38_DIRECT
    _xr38_provider(monkeypatch, {quote: ["99999999999999", "1E-10", "0.00000000019", "1.08501234567890", "1.5"]})
    await _xr38_route(base, quote, [(base, quote)])
    story = f"a MOCKFX sync of {base}/{quote} delivering rates at the limits"

    result, events = await _xr38_sync(base, quote, story)

    stored = await _xr38_stored(base, quote)
    expected = dict(zip(XR38_DAYS, (Decimal("99999999999999"), Decimal("1E-10"), Decimal("1E-10"), Decimal("1.0850123456"), Decimal("1.5")), strict=True))
    assert stored == expected, f"{story} stored {stored}: expected {expected}"
    assert result.status == SyncStatus.OK, f"{story}: the pair is {result.status}, {result.errors}"
    warnings = _xr38_warnings(events, quote)
    assert not warnings, f"{story} logged {warnings}: nothing was skipped"


@pytest.mark.asyncio
@pytest.mark.usefixtures("xr38_pairs")
async def test_xr38_guard_sync_checks_the_rate_it_stores_not_the_rate_quoted(monkeypatch):
    """Guard: green today and after. BIF/EUR is stored inverted: EUR → BIF 1E-11 and 1E-13, which fx_rates.rate could not
    keep as they are, are stored as their inverses, 1E+11 and 1E+13, within the 14 digits. The limit is checked on the rate
    stored, after the normalization, never on the rate quoted."""
    base, quote = XR38_INVERTED
    _xr38_provider(monkeypatch, {base: ["1E-11", "2", "1E-13", "4", "8"]})
    await _xr38_route(base, quote, [(base, quote)])
    story = f"a MOCKFX sync of {base}/{quote} delivering EUR → {base} 1E-11 on {XR38_DAYS[0]} and 1E-13 on {XR38_DAYS[2]}"

    result, events = await _xr38_sync(base, quote, story)

    stored = await _xr38_stored(base, quote)
    expected = dict(zip(XR38_DAYS, (Decimal("1E+11"), Decimal("0.5"), Decimal("1E+13"), Decimal("0.25"), Decimal("0.125")), strict=True))
    assert stored == expected, f"{story} stored {stored}: expected {expected}, the inverses"
    assert result.status == SyncStatus.OK, f"{story}: the pair is {result.status}, {result.errors}"
    warnings = _xr38_warnings(events, base)
    assert not warnings, f"{story} logged {warnings}: nothing was skipped"


@pytest.mark.asyncio
@pytest.mark.usefixtures("xr38_pairs")
@pytest.mark.parametrize("planted", _XR38_LEGACY)
async def test_xr38_sync_overwrites_a_legacy_rate_no_column_can_keep(monkeypatch, planted):
    """Red today for inf and 1e60: ``_count_actual_changes`` truncates the stored rate to compare it and raises
    ``InvalidOperation``; the route fails and the legacy rate stays. Green today for 0 and 1e19.

    Contract (X-R38): reads never raise. The legacy rate compares as a change: the new rate of 1.5 overwrites it, one point
    changed.
    """
    base, quote = XR38_DIRECT
    await _xr38_plant(base, quote, XR38_DAYS[0], planted)
    _xr38_provider(monkeypatch, {quote: ["1.5", None, None, None, None]})
    await _xr38_route(base, quote, [(base, quote)])
    story = f"a MOCKFX sync of {base}/{quote} delivering 1.5 on {XR38_DAYS[0]}, where a legacy {planted!r} is stored"

    result, _events = await _xr38_sync(base, quote, story)

    stored = await _xr38_stored(base, quote)
    assert stored == {XR38_DAYS[0]: Decimal("1.5")}, f"{story} left {stored}: expected 1.5, the new rate overwriting the legacy one; the pair: {result.status} {result.errors}"
    assert (result.status, result.points_changed) == (SyncStatus.OK, 1), f"{story}: the pair is {result.status} with {result.points_changed} point(s) changed, expected ok with 1"


@pytest.mark.asyncio
@pytest.mark.usefixtures("xr38_pairs")
@pytest.mark.parametrize(
    ("pair", "delivered"),
    [
        pytest.param(XR38_DIRECT, "1E+15", id="EUR-UGX-1E+15"),
        pytest.param(XR38_DIRECT, "1E+50", id="EUR-UGX-1E+50"),
        pytest.param(XR38_DIRECT, "1E-11", id="EUR-UGX-1E-11"),
        pytest.param(XR38_INVERTED, "1E-15", id="BIF-EUR-1E-15-inverse-1E+15"),
        pytest.param(XR38_INVERTED, "0", id="BIF-EUR-0-no-inverse"),
    ],
)
async def test_xr38_ensure_rates_multi_source_skips_a_rate_no_column_can_keep_and_stores_the_others(monkeypatch, pair, delivered):
    """Red today: the unwired orchestrator stores 1E+15 as it is, 1E-11 as 0 and the inverse of 1E-15, 1E+15; it raises
    ``InvalidOperation`` on 1E+50 (``truncate_fx_rate``) and ``DivisionByZero`` on the inverse of 0, nothing stored.

    Contract (X-R38), the same as ``sync_pairs_bulk``'s: days 1 and 3 skipped, days 0, 2 and 4 stored, nothing raised, one
    warning naming the pair.
    """
    base, quote = pair
    quoted = _xr38_quoted(pair)
    deliveries, expected = _xr38_around(pair, delivered)
    _xr38_provider(monkeypatch, {quoted: deliveries})
    story = f"ensure_rates_multi_source of MOCKFX for {quoted}, delivering EUR → {quoted} {delivered} on {XR38_DAYS[1]} and {XR38_DAYS[3]}"

    _summary, events = await _xr38_ensure(quoted, story)

    stored = await _xr38_stored(base, quote)
    assert stored == expected, f"{story} stored {stored}: expected the three other days alone, {expected} (X-R38: skip the rate no column can keep, store the others)"
    warnings = _xr38_warnings(events, quoted)
    assert len(warnings) == 1, f"{story} logged {len(warnings)} warning(s) naming {quoted}: expected one for both skipped days (X-R38: logged once per sync): {warnings}"


@pytest.mark.asyncio
@pytest.mark.usefixtures("xr38_pairs")
@pytest.mark.parametrize("planted", _XR38_LEGACY)
async def test_xr38_ensure_rates_multi_source_overwrites_a_legacy_rate_no_column_can_keep(monkeypatch, planted):
    """Red today for inf and 1e60: the orchestrator truncates the stored rate to compare it and raises
    ``InvalidOperation``, nothing stored. Green today for 0 and 1e19.

    Contract (X-R38): reads never raise. The legacy rate compares as a change: the new rate of 1.5 overwrites it, one rate
    changed.
    """
    base, quote = XR38_DIRECT
    await _xr38_plant(base, quote, XR38_DAYS[0], planted)
    _xr38_provider(monkeypatch, {quote: ["1.5", None, None, None, None]})
    story = f"ensure_rates_multi_source of MOCKFX for {quote}, delivering 1.5 on {XR38_DAYS[0]} where a legacy {planted!r} is stored"

    summary, _events = await _xr38_ensure(quote, story)

    stored = await _xr38_stored(base, quote)
    assert stored == {XR38_DAYS[0]: Decimal("1.5")}, f"{story} left {stored}: expected 1.5, the new rate overwriting the legacy one"
    assert summary["total_changed"] == 1, f"{story} counts {summary['total_changed']} change(s): expected 1"


# ============================================================================
# X-R65 (N83): the provider sync stores no rate dated before 1900-01-01
# ============================================================================
#
# Measured before the cure: sync_pairs_bulk keeps a provider's observation when _is_date_within_sync_range says it lies in
# the requested range, and with the start "min" that range has no floor: an observation dated 1899-12-31, or 0001-01-01,
# is stored, and a backward fill or a replay then walks from it (J's SEC8-1b: about 740 000 days from year one). An
# explicit start before 1900 lets it through the same way.
#
# Contract (X-R65, coordinator decisions 17/10): _is_date_within_sync_range(target, start, end) is False for every target
# before EARLIEST_RANGE_START (1900-01-01), whatever the start, "min" included; 1900-01-01 itself is in; the end bounds
# the range as before. ensure_rates_multi_source has no production caller: out of scope.
#
# The pair is this block's own (no seed and no other test uses SOS): MOCKFX quotes EUR → SOS, stored EUR/SOS as it comes.
# Its rates in the window and its route are wiped before and after each test; the provider is a MockFXProvider whose
# fetch answers the block's days whatever the range asked, behind a fetch cache of the test's own.

XR65_FLOOR = date(1900, 1, 1)  # EARLIEST_RANGE_START: the contract's floor, written here and not read from the code
XR65_PAIR = ("EUR", "SOS")
XR65_END = date(1900, 1, 2)
#: What MOCKFX delivers for SOS, by day: two days before the floor (year one among them), the floor, the day after it.
XR65_DELIVERED = {date(1, 1, 1): "2.5", date(1899, 12, 31): "2.75", XR65_FLOOR: "3", XR65_END: "3.25"}


async def _xr65_wipe() -> None:
    """Drop this block's rates in its window, and its routes."""
    base, quote = XR65_PAIR
    async with AsyncSession(get_async_engine()) as session:
        await session.execute(delete(FxRate).where(FxRate.base == base, FxRate.quote == quote, FxRate.date >= min(XR65_DELIVERED), FxRate.date <= max(XR65_DELIVERED)))
        await session.execute(delete(FxConversionRoute).where(FxConversionRoute.base == base, FxConversionRoute.quote == quote))
        await session.commit()


@pytest.fixture
def xr65_pair():
    """X-R65: this block's pair without a rate in the window nor a route, before and after the test."""
    asyncio.run(_xr65_wipe())
    yield
    asyncio.run(_xr65_wipe())


def _xr65_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    """MOCKFX handed out as a MockFXProvider whose fetch answers ``XR65_DELIVERED`` for each currency asked, quoted
    EUR → currency, whatever the range; the fetch cache is the test's own."""
    provider = MockFXProvider()

    async def fetch_rates(date_range, currencies, base_currency=None):
        return {currency: [(day, "EUR", currency, Decimal(rate)) for day, rate in XR65_DELIVERED.items()] for currency in currencies}

    cached = {}
    cache = Mock()
    cache.get.side_effect = lambda key: (cached.get(key), key in cached)
    cache.set.side_effect = cached.__setitem__
    monkeypatch.setattr(provider, "fetch_rates", fetch_rates)
    monkeypatch.setattr(fx_service.FXProviderRegistry, "get_provider_instance", lambda code: provider if code == "MOCKFX" else None)
    monkeypatch.setattr(fx_service, "_fx_fetch_cache", cache)


def test_xr65_sync_range_has_a_floor_at_1900_whatever_the_start():
    """Red today: with the start "min" every day up to the end is in range, 1899-12-31 and 0001-01-01 included; with an
    explicit start before 1900, every day from it.

    Contract (X-R65): a day before 1900-01-01 is out of range whatever the start; 1900-01-01 is in, with "min" as with an
    earlier start; a day after the end stays out.
    """
    cases = [
        (date(1899, 12, 31), "min", date(1900, 1, 3), False),
        (date(1, 1, 1), "min", date(2025, 1, 1), False),
        (date(1899, 12, 31), date(1899, 12, 1), date(1900, 1, 3), False),
        (date.min, date.min, date.max, False),
        (XR65_FLOOR, "min", date(1900, 1, 3), True),
        (XR65_FLOOR, date(1899, 12, 1), date(1900, 1, 3), True),
        (date(1900, 1, 4), "min", date(1900, 1, 3), False),
    ]
    wrong = []
    for target, start, end, expected in cases:
        answer = _is_date_within_sync_range(target, start, end)
        if answer is not expected:
            wrong.append(f"{target} with start {start!r} and end {end}: {answer}, expected {expected}")
    assert not wrong, f"_is_date_within_sync_range answered {wrong}"


@pytest.mark.asyncio
@pytest.mark.usefixtures("xr65_pair")
@pytest.mark.parametrize("start", [pytest.param("min", id="start-min"), pytest.param(date(1899, 12, 31), id="start-1899-12-31")])
async def test_xr65_sync_stores_no_rate_before_1900(monkeypatch, start):
    """Red today: MOCKFX delivers EUR → SOS on 0001-01-01, 1899-12-31, 1900-01-01 and 1900-01-02; synced up to 1900-01-02,
    the four days are stored from "min", and the three from 1899-12-31 on from that start.

    Contract (X-R65): whatever the start, the pair stores 1900-01-01 and 1900-01-02 alone, as delivered, and its result
    is ``ok``.
    """
    base, quote = XR65_PAIR
    _xr65_provider(monkeypatch)
    await _xr38_route(base, quote, [(base, quote)])

    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        response = await sync_pairs_bulk(session, pairs=[f"{base}-{quote}"], date_range=(start, XR65_END))

    result = next(item for item in response.results if item.pair == f"{base}-{quote}")
    async with AsyncSession(get_async_engine()) as session:
        rows = (await session.execute(select(FxRate.date, FxRate.rate).where(FxRate.base == base, FxRate.quote == quote, FxRate.date <= XR65_END))).all()
    stored = {row.date: row.rate for row in rows}
    assert stored == {XR65_FLOOR: Decimal("3"), XR65_END: Decimal("3.25")}, f"synced from {start!r} up to {XR65_END}, EUR/SOS stored {stored}"
    assert result.status == "ok", result
