"""Focused tests for the FX non-technical/core AI Export components (workstream E2 slice).

Covers exactly the five FX "core" component IDs owned by
`backend.app.services.ai_export.components.fx_core`: `fx.pair_identity`,
`fx.current_rate`, `fx.conversion_provenance`, `fx.exposure_base_quote`,
`fx.exposure_provenance`.

Uses a real `AsyncSession` against the test database (real `User`/`Broker`/
`BrokerUserAccess`/`Asset`/`Transaction`/`PriceHistory`/`FxRate` rows), matching
the established integration-test pattern in
`backend/test_scripts/test_services/test_financial/test_portfolio_service.py`:
this is required to faithfully exercise "real direct exposure" (real
`PortfolioService.get_report`) and real `convert_bulk`/`FxRate.source`
provenance, never fakes.

The FX *technical* components (`fx.rate_ohlc`, `fx.returns_volatility`,
`fx.indicators`, `fx.states_events`) belong to a sibling workstream and are
never referenced here.
"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from decimal import Decimal

import pytest
import pytest_asyncio

from backend.app.config import PROJECT_ROOT

sys.path.insert(0, str(PROJECT_ROOT))

from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import backend.app.services.ai_export.components.fx_core as fx_core_module
import backend.app.services.ai_export.components.technical_shared as technical_shared_module
import backend.app.services.portfolio_service as portfolio_service_module
from backend.app.db.models import Asset, AssetType, Broker, BrokerUserAccess, FxRate, PriceHistory, Transaction, TransactionType, User
from backend.app.db.session import get_async_engine
from backend.app.schemas.common import Currency
from backend.app.schemas.portfolio import PortfolioHolding, PortfolioReportMetadata, PortfolioReportResponse, PortfolioSummary
from backend.app.services.ai_export.components.fx_core import FX_CORE_COMPONENTS
from backend.app.services.ai_export.components.fx_payloads import (
    FxExposureBaseQuotePayload,
    FxExposureConversionBasis,
    FxExposureKind,
    FxExposureLinkage,
    FxExposureProvenancePayload,
    FxExposureRole,
    FxExposureSummary,
    FxRateDirection,
)
from backend.app.services.ai_export.components.fx_timing_context import (
    FX_TIMING_CONTEXT_COMPONENTS,
    REASON_FLAT_RANGE,
    REASON_HISTORY_STARTS_LATE,
    FxNeutralScenarioInput,
    FxTimingContextPayload,
)
from backend.app.services.ai_export.components.registry import ComponentRegistry
from backend.app.services.ai_export.components.technical_context import FX_TECHNICAL_CONTEXT_COMPONENTS
from backend.app.services.ai_export.components.technical_shared import FxRateHistoryError, load_fx_rate_series
from backend.app.services.ai_export.components.types import BuildScope, DetailLevel, Domain
from backend.app.services.ai_export.dependencies import BuildContext, RequiredComponentBuildError, ResourceLoadError, build_bucket_plan_for_scope
from backend.app.services.fx import RateNotFoundError, convert_bulk
from backend.app.services.portfolio_service import PortfolioService, _portfolio_l2_cache, _wac_cache
from backend.app.utils.datetime_utils import utcnow

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture(scope="module")
def engine():
    return get_async_engine()


@pytest_asyncio.fixture
async def session(engine):
    _wac_cache.clear()
    _portfolio_l2_cache.clear()
    async with AsyncSession(engine, expire_on_commit=False) as s:
        yield s
        await s.rollback()


@pytest_asyncio.fixture
async def test_user(session) -> User:
    user = User(
        username=f"fxcomp_{utcnow().timestamp()}",
        email=f"fxcomp_{utcnow().timestamp()}@test.com",
        hashed_password="fakehash",
        is_active=True,
    )
    session.add(user)
    await session.flush()
    return user


# =============================================================================
# HELPERS
# =============================================================================


def _registry() -> ComponentRegistry:
    return ComponentRegistry(FX_CORE_COMPONENTS)


def _scope(
    *,
    user_id: int,
    base: str = "EUR",
    quote: str = "USD",
    target: str = "EUR",
    start: date = date(2025, 1, 1),
    end: date = date(2025, 1, 10),
    broker_scope: tuple[int, ...] = (),
    detail_level: DetailLevel = DetailLevel.STANDARD,
) -> BuildScope:
    return BuildScope(
        request_id=f"req-{user_id}-{base}-{quote}-{target}-{end.isoformat()}-{detail_level.value}",
        user_id=user_id,
        domain=Domain.FX,
        detail_level=detail_level,
        period_start=start,
        period_end=end,
        target_currency=target,
        broker_scope=broker_scope,
        base_currency=base,
        quote_currency=quote,
    )


def _context(session, scope: BuildScope) -> BuildContext:
    bucket_plan = build_bucket_plan_for_scope(scope)
    return BuildContext(_registry(), request_id=scope.request_id, scope=scope, bucket_plan=bucket_plan, session=session)


async def _seed_rate(session, *, base: str, quote: str, rate: str, day: date, source: str = "ECB") -> None:
    """Seeds one `FxRate` row for the (base, quote) pair, normalizing to the alphabetical storage order.

    Upserts rather than blindly inserting: the test database is a shared, persistent
    file (see `backend.test_scripts.test_db_config`), so another concurrently-running
    test suite may have already committed a row for the same (date, base, quote) -
    a plain INSERT would then fail the `uq_fx_rates_date_base_quote` constraint.
    """
    stored_base, stored_quote = sorted((base, quote))
    stored_rate = Decimal(rate) if base == stored_base else Decimal(1) / Decimal(rate)
    existing = (await session.execute(select(FxRate).where(FxRate.date == day, FxRate.base == stored_base, FxRate.quote == stored_quote))).scalar_one_or_none()
    if existing is not None:
        existing.rate = stored_rate
        existing.source = source
        session.add(existing)
    else:
        session.add(FxRate(date=day, base=stored_base, quote=stored_quote, rate=stored_rate, source=source))
    await session.flush()


async def _seed_warmup_anchor(session, *, base: str, quote: str, rate: str) -> None:
    """Seeds one very old `FxRate` anchor so `fx.current_rate`/`fx.conversion_provenance`'s
    warm-up-inclusive series load (`technical_shared.load_fx_rate_series`, shared with the
    FX technical wave - parent integration gate, requirement 4) always has *some* rate to
    unlimited-backward-fill from for every warm-up date, without affecting the exact/backward-fill
    behavior under test for the visible dates (those are still seeded by the caller as before).
    """
    await _seed_rate(session, base=base, quote=quote, rate=rate, day=date(1990, 1, 1), source="ECB")


async def _make_broker(session, user: User, *, name: str) -> Broker:
    broker = Broker(name=f"{name}_{utcnow().timestamp()}")
    session.add(broker)
    await session.flush()
    session.add(BrokerUserAccess(broker_id=broker.id, user_id=user.id, role="OWNER", share_percentage=Decimal("1.0")))
    await session.flush()
    return broker


async def _deposit(session, broker: Broker, *, amount: str, currency: str, day: date) -> None:
    session.add(Transaction(broker_id=broker.id, type=TransactionType.DEPOSIT, date=day, amount=Decimal(amount), currency=currency))
    await session.flush()


async def _make_asset(session, *, currency: str, ticker: str, quote_base_quantity: int = 1) -> Asset:
    asset = Asset(display_name=f"FxCompAsset_{ticker}_{utcnow().timestamp()}", ticker=ticker, currency=currency, type=AssetType.STOCK, quote_base_quantity=quote_base_quantity)
    session.add(asset)
    await session.flush()
    return asset


async def _buy(session, broker: Broker, asset: Asset, *, quantity: str, amount: str, currency: str, day: date) -> None:
    session.add(
        Transaction(
            broker_id=broker.id,
            asset_id=asset.id,
            type=TransactionType.BUY,
            date=day,
            quantity=Decimal(quantity),
            amount=Decimal(amount),
            currency=currency,
        )
    )
    await session.flush()


async def _price(session, asset: Asset, *, day: date, close: str, currency: str) -> None:
    session.add(
        PriceHistory(
            asset_id=asset.id,
            date=day,
            open=Decimal(close),
            high=Decimal(close),
            low=Decimal(close),
            close=Decimal(close),
            volume=Decimal("1"),
            currency=currency,
            source_plugin_key="manual_test",
        )
    )
    await session.flush()


def _row_key(row) -> tuple:
    return (row.kind.value, row.linkage.value, row.linked_currency, row.broker_id, row.asset_id)


# =============================================================================
# fx.pair_identity
# =============================================================================


class TestPairIdentity:
    @pytest.mark.asyncio
    async def test_direct_pair(self, session, test_user):
        scope = _scope(user_id=test_user.id, base="EUR", quote="USD")
        context = _context(session, scope)
        envelope = await context.resolve("fx.pair_identity", required=True)
        assert envelope.payload["base_currency"] == "EUR"
        assert envelope.payload["quote_currency"] == "USD"
        assert envelope.payload["stored_base_currency"] == "EUR"
        assert envelope.payload["stored_quote_currency"] == "USD"
        assert envelope.payload["direction"] == FxRateDirection.DIRECT.value

    @pytest.mark.asyncio
    async def test_inverse_pair(self, session, test_user):
        # CHF < USD alphabetically, so requesting base=USD/quote=CHF is inverse.
        scope = _scope(user_id=test_user.id, base="USD", quote="CHF")
        context = _context(session, scope)
        envelope = await context.resolve("fx.pair_identity", required=True)
        assert envelope.payload["stored_base_currency"] == "CHF"
        assert envelope.payload["stored_quote_currency"] == "USD"
        assert envelope.payload["direction"] == FxRateDirection.INVERSE.value

    @pytest.mark.asyncio
    async def test_succeeds_without_any_fx_rate_rows(self, session, test_user):
        """pair_identity is pure scope math - must succeed with zero FxRate rows present."""
        scope = _scope(user_id=test_user.id, base="EUR", quote="GBP", start=date(2031, 1, 1), end=date(2031, 1, 1))
        context = _context(session, scope)
        envelope = await context.resolve("fx.pair_identity", required=True)
        assert envelope.payload["direction"] == FxRateDirection.DIRECT.value  # 'E' < 'G'


# =============================================================================
# fx.current_rate
# =============================================================================


class TestCurrentRate:
    @pytest.mark.asyncio
    async def test_exact_date_rate_is_not_backward_filled(self, session, test_user):
        scope = _scope(user_id=test_user.id, base="EUR", quote="USD", start=date(2025, 2, 1), end=date(2025, 2, 5))
        await _seed_warmup_anchor(session, base="EUR", quote="USD", rate="1.10")
        for offset in range(5):
            await _seed_rate(session, base="EUR", quote="USD", rate="1.10", day=date(2025, 2, 1 + offset))
        context = _context(session, scope)
        envelope = await context.resolve("fx.current_rate", required=True)
        assert envelope.payload["requested_date"] == "2025-02-05"
        assert envelope.payload["effective_date"] == "2025-02-05"
        assert envelope.payload["is_backward_filled"] is False
        assert envelope.payload["staleness_days"] == 0
        assert envelope.payload["direction"] == FxRateDirection.DIRECT.value
        assert Decimal(envelope.payload["rate"]) == Decimal("1.10")

    @pytest.mark.asyncio
    async def test_backward_fill_when_no_exact_rate(self, session, test_user):
        scope = _scope(user_id=test_user.id, base="EUR", quote="USD", start=date(2025, 3, 1), end=date(2025, 3, 5))
        await _seed_warmup_anchor(session, base="EUR", quote="USD", rate="1.05")
        # Only seed the first day of the period - later days must backward-fill from it.
        await _seed_rate(session, base="EUR", quote="USD", rate="1.05", day=date(2025, 3, 1))
        context = _context(session, scope)
        envelope = await context.resolve("fx.current_rate", required=True)
        assert envelope.payload["requested_date"] == "2025-03-05"
        assert envelope.payload["effective_date"] == "2025-03-01"
        assert envelope.payload["is_backward_filled"] is True
        assert envelope.payload["staleness_days"] == 4
        assert Decimal(envelope.payload["rate"]) == Decimal("1.05")

    @pytest.mark.asyncio
    async def test_inverse_direction_current_rate(self, session, test_user):
        scope = _scope(user_id=test_user.id, base="USD", quote="CHF", start=date(2025, 4, 1), end=date(2025, 4, 1))
        # 1.25 has an exact reciprocal (0.80), so the stored CHF/USD rate round-trips
        # back to an exact Decimal - no floating-point-style rounding noise to tolerate.
        await _seed_warmup_anchor(session, base="USD", quote="CHF", rate="1.25")
        await _seed_rate(session, base="USD", quote="CHF", rate="1.25", day=date(2025, 4, 1))
        context = _context(session, scope)
        envelope = await context.resolve("fx.current_rate", required=True)
        assert envelope.payload["direction"] == FxRateDirection.INVERSE.value
        assert Decimal(envelope.payload["rate"]) == Decimal("1.25")

    @pytest.mark.asyncio
    async def test_required_failure_when_no_rate_at_all(self, session, test_user):
        """No fabricated route: a missing rate must propagate as a required failure, never a fake success."""
        scope = _scope(user_id=test_user.id, base="EUR", quote="AUD", start=date(2025, 5, 1), end=date(2025, 5, 1))
        context = _context(session, scope)
        with pytest.raises(RequiredComponentBuildError) as excinfo:
            await context.resolve("fx.current_rate", required=True)
        assert isinstance(excinfo.value.cause.cause if hasattr(excinfo.value.cause, "cause") else excinfo.value.cause, (RateNotFoundError, Exception))


# =============================================================================
# fx.conversion_provenance
# =============================================================================


class TestConversionProvenance:
    @pytest.mark.asyncio
    async def test_source_reflects_stored_value(self, session, test_user):
        scope = _scope(user_id=test_user.id, base="EUR", quote="USD", start=date(2025, 6, 1), end=date(2025, 6, 1))
        await _seed_warmup_anchor(session, base="EUR", quote="USD", rate="1.08")
        await _seed_rate(session, base="EUR", quote="USD", rate="1.08", day=date(2025, 6, 1), source="MANUAL")
        context = _context(session, scope)
        envelope = await context.resolve("fx.conversion_provenance", required=True)
        assert envelope.payload["source"] == "MANUAL"
        assert envelope.payload["is_backward_filled"] is False
        assert envelope.payload["direction"] == FxRateDirection.DIRECT.value

    @pytest.mark.asyncio
    async def test_source_reflects_default_ecb(self, session, test_user):
        scope = _scope(user_id=test_user.id, base="EUR", quote="USD", start=date(2025, 6, 10), end=date(2025, 6, 10))
        await _seed_warmup_anchor(session, base="EUR", quote="USD", rate="1.09")
        await _seed_rate(session, base="EUR", quote="USD", rate="1.09", day=date(2025, 6, 10))
        context = _context(session, scope)
        envelope = await context.resolve("fx.conversion_provenance", required=True)
        assert envelope.payload["source"] == "ECB"

    @pytest.mark.asyncio
    async def test_memoized_rate_series_across_current_rate_and_conversion_provenance(self, session, test_user, monkeypatch):
        scope = _scope(user_id=test_user.id, base="EUR", quote="USD", start=date(2025, 7, 1), end=date(2025, 7, 3))
        await _seed_warmup_anchor(session, base="EUR", quote="USD", rate="1.11")
        for offset in range(3):
            await _seed_rate(session, base="EUR", quote="USD", rate="1.11", day=date(2025, 7, 1 + offset))

        call_count = {"n": 0}
        real_convert_bulk = convert_bulk

        async def _counting_convert_bulk(*args, **kwargs):
            call_count["n"] += 1
            return await real_convert_bulk(*args, **kwargs)

        # `fx.current_rate`/`fx.conversion_provenance` delegate to the technical
        # sibling wave's `load_fx_rate_series` (parent integration gate,
        # requirement 4), so the batched `convert_bulk` call happens under
        # `technical_shared`'s own module binding, not `fx_core`'s.
        monkeypatch.setattr(technical_shared_module, "convert_bulk", _counting_convert_bulk)

        context = _context(session, scope)
        await context.resolve("fx.current_rate", required=True)
        await context.resolve("fx.conversion_provenance", required=True)

        # One batched convert_bulk call for the whole warm-up+visible period, shared by both components.
        assert call_count["n"] == 1


# =============================================================================
# fx.exposure_base_quote / fx.exposure_provenance - empty exposure
# =============================================================================


class TestExposureEmpty:
    @pytest.mark.asyncio
    async def test_empty_exposure_is_valid_success(self, session, test_user):
        await _make_broker(session, test_user, name="EmptyBroker")
        scope = _scope(user_id=test_user.id, base="EUR", quote="USD", target="EUR", start=date(2025, 1, 1), end=date(2025, 1, 5))
        context = _context(session, scope)

        base_quote_envelope = await context.resolve("fx.exposure_base_quote", required=True)
        assert base_quote_envelope.payload["rows"] == []

        provenance_envelope = await context.resolve("fx.exposure_provenance", required=True)
        assert provenance_envelope.payload["conversions"] == []


# =============================================================================
# fx.exposure_base_quote - real cash + position exposure
# =============================================================================


class TestExposureCashAndPositions:
    @pytest_asyncio.fixture
    async def scenario(self, session, test_user):
        """One broker with: EUR cash (matches pair), a USD-trading position (matches pair), a JPY position (must be excluded - no look-through).

        Both BUYs settle in EUR (the broker's cash currency) so only the intended
        EUR cash row appears - a BUY settled in the asset's own trading currency
        would also create its own implicit foreign cash balance row, which is a
        real, separate exposure fact but not what these tests are isolating.
        """
        broker = await _make_broker(session, test_user, name="CashPosBroker")
        await _deposit(session, broker, amount="5000", currency="EUR", day=date(2025, 1, 1))

        usd_asset = await _make_asset(session, currency="USD", ticker="USDA")
        await _buy(session, broker, usd_asset, quantity="10", amount="-900", currency="EUR", day=date(2025, 1, 1))
        await _price(session, usd_asset, day=date(2025, 1, 1), close="100", currency="USD")

        jpy_asset = await _make_asset(session, currency="JPY", ticker="JPYA")
        await _buy(session, broker, jpy_asset, quantity="5", amount="-100", currency="EUR", day=date(2025, 1, 1))
        # Real JPY-denominated market price so valuation_effective_currency resolves to
        # the asset's own currency (JPY) rather than falling back to the EUR-settled
        # transaction cost basis - otherwise it would spuriously match the EUR leg of
        # the pair via VALUATION_CURRENCY, which is not what "no look-through" is testing.
        await _price(session, jpy_asset, day=date(2025, 1, 1), close="1000", currency="JPY")

        await _seed_rate(session, base="EUR", quote="USD", rate="1.10", day=date(2025, 1, 1))
        await _seed_rate(session, base="EUR", quote="JPY", rate="160", day=date(2025, 1, 1))
        return broker, usd_asset, jpy_asset

    @pytest.mark.asyncio
    async def test_cash_and_trading_currency_rows_present_with_correct_linkage(self, session, test_user, scenario):
        broker, usd_asset, _jpy_asset = scenario
        scope = _scope(user_id=test_user.id, base="EUR", quote="USD", target="EUR", start=date(2025, 1, 1), end=date(2025, 1, 1))
        context = _context(session, scope)
        envelope = await context.resolve("fx.exposure_base_quote", required=True)
        payload = FxExposureBaseQuotePayload.model_validate(envelope.payload)

        cash_rows = [row for row in payload.rows if row.kind is FxExposureKind.CASH]
        position_rows = [row for row in payload.rows if row.kind is FxExposureKind.POSITION]

        assert len(cash_rows) == 1
        assert cash_rows[0].linked_currency == "EUR"
        assert cash_rows[0].linkage is FxExposureLinkage.CASH_CURRENCY
        assert cash_rows[0].native_amount == Decimal("4000")  # 5000 deposit - 900 - 100 EUR-settled BUYs
        assert cash_rows[0].broker_id == broker.id

        assert len(position_rows) == 1
        assert position_rows[0].linked_currency == "USD"
        assert position_rows[0].linkage is FxExposureLinkage.TRADING_CURRENCY
        assert position_rows[0].asset_id == usd_asset.id

    @pytest.mark.asyncio
    async def test_position_native_and_target_amounts_are_not_double_converted(self, session, test_user, scenario):
        """CRITICAL regression: `holding.current_value` is already expressed in
        `target_currency` by the portfolio valuation engine and must never be
        treated as a native amount and reconverted a second time.

        10 units @ $100 USD = 1000 USD native; at EUR/USD=1.10 that is
        ~909.09 EUR in target_currency - never ~826.44 EUR (which is what a
        double conversion, 909.09 USD "native" * 0.9090909... again, would
        incorrectly produce).
        """
        _broker, usd_asset, _jpy_asset = scenario
        scope = _scope(user_id=test_user.id, base="EUR", quote="USD", target="EUR", start=date(2025, 1, 1), end=date(2025, 1, 1))
        context = _context(session, scope)
        envelope = await context.resolve("fx.exposure_base_quote", required=True)
        payload = FxExposureBaseQuotePayload.model_validate(envelope.payload)

        position_row = next(row for row in payload.rows if row.asset_id == usd_asset.id)
        assert position_row.native_amount is not None
        assert abs(position_row.native_amount - Decimal("1000")) < Decimal("0.01")
        assert abs(position_row.target_amount - Decimal("909.0909090909090909090909091")) < Decimal("0.01")
        assert abs(position_row.target_amount - Decimal("826.4462809917355371900826446")) > Decimal("1")
        assert position_row.conversion.basis is FxExposureConversionBasis.RESOLVED_RATE
        assert position_row.conversion.direction is FxRateDirection.INVERSE  # stored EUR<USD; USD->EUR divides
        assert position_row.valuation_source == "MARKET_PRICE"

    @pytest.mark.asyncio
    async def test_non_reconciling_resolved_rate_falls_back_to_engine_valuation_with_native_none(self, session, test_user, scenario, monkeypatch):
        """CRITICAL regression: when a *known* native_amount does not reconcile with the
        independently-resolved rate, `_position_row_conversion` correctly falls back to
        ENGINE_VALUATION - but the row builder must also null out `native_amount` for
        that row (never pass through the known-but-now-untrusted `candidate.native_amount`
        alongside an ENGINE_VALUATION basis, which `FxExposureRow` rejects as an
        inconsistent, fabricated-looking pairing).

        Forces the non-reconciling branch via `_rate_reconciles` (rather than a
        contrived scenario) since honest native/target amounts derived from the same
        underlying `convert_bulk` call reconcile near-exactly in every real case.
        """
        _broker, usd_asset, _jpy_asset = scenario
        monkeypatch.setattr(fx_core_module, "_rate_reconciles", lambda *_args, **_kwargs: False)
        scope = _scope(user_id=test_user.id, base="EUR", quote="USD", target="EUR", start=date(2025, 1, 1), end=date(2025, 1, 1))
        context = _context(session, scope)
        envelope = await context.resolve("fx.exposure_base_quote", required=True)
        payload = FxExposureBaseQuotePayload.model_validate(envelope.payload)

        position_row = next(row for row in payload.rows if row.asset_id == usd_asset.id)
        assert position_row.conversion.basis is FxExposureConversionBasis.ENGINE_VALUATION
        assert position_row.native_amount is None  # known (1000 USD) but discarded: it no longer reconciles
        assert position_row.conversion.direction is None  # no rate/source claimed for this row
        assert abs(position_row.target_amount - Decimal("909.0909090909090909090909091")) < Decimal("0.01")  # preserved, engine-owned
        assert position_row.valuation_source == "MARKET_PRICE"

    @pytest.mark.asyncio
    async def test_no_look_through_excludes_unrelated_currency(self, session, test_user, scenario):
        _broker, _usd_asset, jpy_asset = scenario
        scope = _scope(user_id=test_user.id, base="EUR", quote="USD", target="EUR", start=date(2025, 1, 1), end=date(2025, 1, 1))
        context = _context(session, scope)
        envelope = await context.resolve("fx.exposure_base_quote", required=True)
        payload = FxExposureBaseQuotePayload.model_validate(envelope.payload)
        assert all(row.asset_id != jpy_asset.id for row in payload.rows)
        assert all(row.linked_currency != "JPY" for row in payload.rows)

    @pytest.mark.asyncio
    async def test_deterministic_row_order_across_fresh_contexts(self, session, test_user, scenario):
        """Two independent `BuildContext`s (as two separate requests would get) over the same
        underlying data must produce byte-identical, deterministically-ordered rows."""
        scope = _scope(user_id=test_user.id, base="EUR", quote="USD", target="EUR", start=date(2025, 1, 1), end=date(2025, 1, 1))

        context_a = _context(session, scope)
        envelope_a = await context_a.resolve("fx.exposure_base_quote", required=True)

        context_b = _context(session, scope)
        envelope_b = await context_b.resolve("fx.exposure_base_quote", required=True)

        assert envelope_a.payload["rows"] == envelope_b.payload["rows"]
        payload_a = FxExposureBaseQuotePayload.model_validate(envelope_a.payload)
        keys = [_row_key(row) for row in payload_a.rows]
        assert keys == sorted(keys)

    @pytest.mark.asyncio
    async def test_all_detail_levels_preserve_full_cardinality(self, session, test_user, scenario):
        row_counts = set()
        for detail_level in DetailLevel:
            scope = _scope(user_id=test_user.id, base="EUR", quote="USD", target="EUR", start=date(2025, 1, 1), end=date(2025, 1, 1), detail_level=detail_level)
            context = _context(session, scope)
            envelope = await context.resolve("fx.exposure_base_quote", required=True)
            row_counts.add(len(envelope.payload["rows"]))
        assert row_counts == {2}  # no top-N truncation at any detail level


# =============================================================================
# fx.exposure_base_quote - valuation currency differs from trading currency
# =============================================================================


class TestExposureMismatchedValuationCurrency:
    @pytest.mark.asyncio
    async def test_valuation_currency_differs_from_trading_currency_no_fabricated_native(self, session, test_user):
        """Asset trades/settles in USD (`Asset.currency`), but its most authoritative
        market price at the snapshot date happens to be sourced in GBP (e.g. a
        dual-listed instrument) - `valuation_effective_currency` differs from
        `trading_currency` and GBP is not in the EUR/USD pair. The row must still
        surface as real USD exposure (trading_currency linkage), but must not
        fabricate a native USD amount by dividing/multiplying the GBP-denominated
        value - `native_amount` must be `None` and `conversion.basis` must be
        `ENGINE_VALUATION` (target_amount only, no invented rate)."""
        broker = await _make_broker(session, test_user, name="MismatchBroker")
        usd_asset = await _make_asset(session, currency="USD", ticker="USDGBP")
        await _buy(session, broker, usd_asset, quantity="10", amount="-900", currency="EUR", day=date(2025, 1, 1))
        await _price(session, usd_asset, day=date(2025, 1, 1), close="80", currency="GBP")
        await _seed_rate(session, base="EUR", quote="USD", rate="1.10", day=date(2025, 1, 1))
        await _seed_rate(session, base="EUR", quote="GBP", rate="0.85", day=date(2025, 1, 1))

        scope = _scope(user_id=test_user.id, base="EUR", quote="USD", target="EUR", start=date(2025, 1, 1), end=date(2025, 1, 1))
        context = _context(session, scope)
        envelope = await context.resolve("fx.exposure_base_quote", required=True)
        payload = FxExposureBaseQuotePayload.model_validate(envelope.payload)

        position_row = next(row for row in payload.rows if row.asset_id == usd_asset.id)
        assert position_row.linked_currency == "USD"
        assert position_row.linkage is FxExposureLinkage.TRADING_CURRENCY
        assert position_row.native_amount is None  # no honest USD amount: valuation was actually in GBP
        assert position_row.target_amount is not None
        assert position_row.conversion.basis is FxExposureConversionBasis.ENGINE_VALUATION
        assert position_row.conversion.direction is None
        assert position_row.valuation_source == "MARKET_PRICE"

    @pytest.mark.asyncio
    async def test_engine_valuation_only_currency_excluded_from_provenance(self, session, test_user):
        """`fx.exposure_provenance` must never claim a resolved conversion as
        provenance for a currency whose only `fx.exposure_base_quote` row(s)
        fell back to `ENGINE_VALUATION` (no conversion was actually applied to
        any of them) - USD here only appears via the mismatched-valuation
        position row, so it must be entirely absent from `conversions`."""
        broker = await _make_broker(session, test_user, name="MismatchProvBroker")
        usd_asset = await _make_asset(session, currency="USD", ticker="USDGBP2")
        await _buy(session, broker, usd_asset, quantity="10", amount="-900", currency="EUR", day=date(2025, 1, 1))
        await _price(session, usd_asset, day=date(2025, 1, 1), close="80", currency="GBP")
        await _seed_rate(session, base="EUR", quote="USD", rate="1.10", day=date(2025, 1, 1))
        await _seed_rate(session, base="EUR", quote="GBP", rate="0.85", day=date(2025, 1, 1))

        scope = _scope(user_id=test_user.id, base="EUR", quote="USD", target="EUR", start=date(2025, 1, 1), end=date(2025, 1, 1))
        context = _context(session, scope)
        base_quote_envelope = await context.resolve("fx.exposure_base_quote", required=True)
        base_quote_payload = FxExposureBaseQuotePayload.model_validate(base_quote_envelope.payload)
        position_row = next(row for row in base_quote_payload.rows if row.asset_id == usd_asset.id)
        assert position_row.conversion.basis is FxExposureConversionBasis.ENGINE_VALUATION

        provenance_envelope = await context.resolve("fx.exposure_provenance", required=True)
        provenance_payload = FxExposureProvenancePayload.model_validate(provenance_envelope.payload)
        assert "USD" not in {entry.linked_currency for entry in provenance_payload.conversions}


# =============================================================================
# fx.exposure_base_quote - quote_base_quantity scaling
# =============================================================================


class TestExposureQuoteBaseQuantity:
    @pytest.mark.asyncio
    async def test_native_amount_scaled_by_quote_base_quantity(self, session, test_user):
        """A bond-like asset quoted per 100 face value (`quote_base_quantity=100`):
        native_amount must apply the same `(quantity / quote_base_quantity) * price`
        scaling the portfolio valuation engine itself uses
        (`backend.app.utils.financial.valuation_utils.compute_holding_value`),
        never a raw `quantity * price` (which would be 100x too large here)."""
        broker = await _make_broker(session, test_user, name="QuoteBaseBroker")
        bond_asset = await _make_asset(session, currency="USD", ticker="BONDQ", quote_base_quantity=100)
        await _buy(session, broker, bond_asset, quantity="1000", amount="-900", currency="EUR", day=date(2025, 1, 1))
        await _price(session, bond_asset, day=date(2025, 1, 1), close="98", currency="USD")
        await _seed_rate(session, base="EUR", quote="USD", rate="1.10", day=date(2025, 1, 1))

        scope = _scope(user_id=test_user.id, base="EUR", quote="USD", target="EUR", start=date(2025, 1, 1), end=date(2025, 1, 1))
        context = _context(session, scope)
        envelope = await context.resolve("fx.exposure_base_quote", required=True)
        payload = FxExposureBaseQuotePayload.model_validate(envelope.payload)

        position_row = next(row for row in payload.rows if row.asset_id == bond_asset.id)
        assert position_row.native_amount == Decimal("980")  # (1000 / 100) * 98, never 98000
        assert position_row.conversion.basis is FxExposureConversionBasis.RESOLVED_RATE


# =============================================================================
# fx.exposure_base_quote - broker scope
# =============================================================================


class TestExposureBrokerScope:
    @pytest.mark.asyncio
    async def test_broker_scope_filters_to_selected_broker(self, session, test_user):
        broker_a = await _make_broker(session, test_user, name="ScopeBrokerA")
        broker_b = await _make_broker(session, test_user, name="ScopeBrokerB")
        await _deposit(session, broker_a, amount="1000", currency="EUR", day=date(2025, 1, 1))
        await _deposit(session, broker_b, amount="2000", currency="EUR", day=date(2025, 1, 1))

        scope = _scope(user_id=test_user.id, base="EUR", quote="USD", target="EUR", start=date(2025, 1, 1), end=date(2025, 1, 1), broker_scope=(broker_a.id,))
        context = _context(session, scope)
        envelope = await context.resolve("fx.exposure_base_quote", required=True)
        payload = FxExposureBaseQuotePayload.model_validate(envelope.payload)

        assert len(payload.rows) == 1
        assert payload.rows[0].broker_id == broker_a.id
        assert payload.rows[0].native_amount == Decimal("1000")


# =============================================================================
# fx.exposure_provenance - conversion provenance / dedup
# =============================================================================


class TestExposureConversionProvenance:
    @pytest.mark.asyncio
    async def test_conversion_provenance_towards_third_target_currency_and_dedup(self, session, test_user):
        broker_a = await _make_broker(session, test_user, name="ProvBrokerA")
        broker_b = await _make_broker(session, test_user, name="ProvBrokerB")
        # Two EUR cash rows across two brokers - same linked_currency, must dedup to one conversion entry.
        await _deposit(session, broker_a, amount="1000", currency="EUR", day=date(2025, 1, 1))
        await _deposit(session, broker_b, amount="3000", currency="EUR", day=date(2025, 1, 1))
        await _seed_rate(session, base="EUR", quote="GBP", rate="0.85", day=date(2025, 1, 1), source="ECB")

        scope = _scope(user_id=test_user.id, base="EUR", quote="USD", target="GBP", start=date(2025, 1, 1), end=date(2025, 1, 1))
        context = _context(session, scope)
        await context.resolve("fx.exposure_base_quote", required=True)
        provenance_envelope = await context.resolve("fx.exposure_provenance", required=True)
        payload = FxExposureProvenancePayload.model_validate(provenance_envelope.payload)

        assert len(payload.conversions) == 1
        entry = payload.conversions[0]
        assert entry.linked_currency == "EUR"
        assert entry.target_currency == "GBP"
        assert entry.direction == FxRateDirection.DIRECT
        assert entry.source == "ECB"
        assert entry.is_backward_filled is False

    @pytest.mark.asyncio
    async def test_memoized_report_and_conversions_across_both_exposure_components(self, session, test_user, monkeypatch):
        broker = await _make_broker(session, test_user, name="MemoBroker")
        await _deposit(session, broker, amount="1000", currency="EUR", day=date(2025, 1, 1))
        await _seed_rate(session, base="EUR", quote="GBP", rate="0.85", day=date(2025, 1, 1))

        report_calls = {"n": 0}
        real_get_report = PortfolioService.get_report

        async def _counting_get_report(self, user_id, query):
            report_calls["n"] += 1
            return await real_get_report(self, user_id, query)

        monkeypatch.setattr(portfolio_service_module.PortfolioService, "get_report", _counting_get_report)

        convert_calls = {"n": 0}
        real_convert_bulk = convert_bulk

        async def _counting_convert_bulk(*args, **kwargs):
            convert_calls["n"] += 1
            return await real_convert_bulk(*args, **kwargs)

        monkeypatch.setattr(fx_core_module, "convert_bulk", _counting_convert_bulk)

        scope = _scope(user_id=test_user.id, base="EUR", quote="USD", target="GBP", start=date(2025, 1, 1), end=date(2025, 1, 1))
        context = _context(session, scope)
        await context.resolve("fx.exposure_base_quote", required=True)
        await context.resolve("fx.exposure_provenance", required=True)

        assert report_calls["n"] == 1
        assert convert_calls["n"] == 1


# =============================================================================
# fx.exposure_base_quote - no fabricated route
# =============================================================================


class TestExposureNoFabricatedRoute:
    @pytest.mark.asyncio
    async def test_missing_target_conversion_rate_propagates_as_failure(self, session, test_user):
        broker = await _make_broker(session, test_user, name="NoRouteBroker")
        await _deposit(session, broker, amount="1000", currency="EUR", day=date(2025, 1, 1))
        # Deliberately no EUR/JPY FxRate row seeded.
        scope = _scope(user_id=test_user.id, base="EUR", quote="USD", target="JPY", start=date(2025, 1, 1), end=date(2025, 1, 1))
        context = _context(session, scope)
        with pytest.raises(RequiredComponentBuildError):
            await context.resolve("fx.exposure_base_quote", required=True)


# =============================================================================
# fx.exposure_base_quote - required source failure
# =============================================================================


class TestExposureSourceFailure:
    @pytest.mark.asyncio
    async def test_missing_current_value_on_matched_position_is_a_required_failure(self, session, test_user):
        asset = await _make_asset(session, currency="USD", ticker="BADVAL")

        async def _fake_load_exposure_report(context):
            return PortfolioReportResponse(
                metadata=PortfolioReportMetadata(target_currency="EUR", generated_at=date(2025, 1, 1)),
                summary=PortfolioSummary(
                    net_worth=Currency(code="EUR", amount=Decimal("0")),
                    total_invested=Currency(code="EUR", amount=Decimal("0")),
                    total_gain_loss=Currency(code="EUR", amount=Decimal("0")),
                    total_gain_loss_percent=Decimal("0"),
                    cash_total=Currency(code="EUR", amount=Decimal("0")),
                    simple_roi_percent=Decimal("0"),
                    holdings=[
                        PortfolioHolding(
                            asset_id=asset.id,
                            asset_name="Bad Valuation Asset",
                            asset_type="STOCK",
                            quantity=Decimal("1"),
                            current_value=None,
                            valuation_effective_currency=None,
                        )
                    ],
                    by_broker=[],
                ),
            )

        original = fx_core_module._load_exposure_report
        fx_core_module._load_exposure_report = _fake_load_exposure_report
        try:
            scope = _scope(user_id=test_user.id, base="EUR", quote="USD", target="EUR", start=date(2025, 1, 1), end=date(2025, 1, 1))
            context = _context(session, scope)
            with pytest.raises(RequiredComponentBuildError):
                await context.resolve("fx.exposure_base_quote", required=True)
        finally:
            fx_core_module._load_exposure_report = original


# =============================================================================
# FX Partial History (V2, requirement 7)
# =============================================================================


def _fx_technical_registry() -> ComponentRegistry:
    """Registry that includes FX core + FX technical context components."""
    return ComponentRegistry((*FX_CORE_COMPONENTS, *FX_TECHNICAL_CONTEXT_COMPONENTS))


def _fx_technical_context(session, scope: BuildScope) -> BuildContext:
    bucket_plan = build_bucket_plan_for_scope(scope)
    return BuildContext(_fx_technical_registry(), request_id=scope.request_id, scope=scope, bucket_plan=bucket_plan, session=session)


class TestFxPartialHistory:
    """Real-DB tests for FX partial-history coverage semantics (V2 requirement 7).

    Verifies that:
    - Missing pre-source warm-up dates are silently skipped (leading Nones)
    - fx_no_usable_rate is raised when no rate covers period_end
    - fx.technical_coverage succeeds even when some signals are unavailable
    """

    @pytest.mark.asyncio
    async def test_missing_pre_source_warmup_dates_succeed(self, session, test_user):
        """Seeding rates from period_start (not the warmup start) should succeed.

        The warmup window precedes period_start; the dates before our first seeded
        rate will be None → skipped as pre-source gaps. The visible period is
        fully covered → `load_fx_rate_series` succeeds.
        """
        period_start = date(2026, 6, 1)
        period_end = date(2026, 6, 10)

        # Seed only the visible period (no warmup rates) + one anchor for backward-fill
        for offset in range((period_end - period_start).days + 1):
            day = period_start + timedelta(days=offset)
            await _seed_rate(session, base="EUR", quote="USD", rate="1.10", day=day)

        scope = _scope(user_id=test_user.id, base="EUR", quote="USD", target="EUR", start=period_start, end=period_end)
        context = _fx_technical_context(session, scope)
        # Should not raise - pre-source warmup gaps are allowed
        series = await load_fx_rate_series(context)
        assert series is not None
        # The series covers at least the visible period
        obs_dates = {obs.requested_date for obs in series.observations}
        assert period_end in obs_dates

    @pytest.mark.asyncio
    async def test_no_rate_at_or_before_period_end_raises_fx_no_usable_rate(self, session, test_user):
        """When no rate exists at or before period_end, FxRateHistoryError with
        reason_code='fx_no_usable_rate' must be raised (wrapped in ResourceLoadError)."""
        period_start = date(2025, 5, 1)
        period_end = date(2025, 5, 1)

        # EUR/AUD on this date is the same known-absent route used by the core FX failure test above.
        scope = _scope(user_id=test_user.id, base="EUR", quote="AUD", target="EUR", start=period_start, end=period_end)
        context = _fx_technical_context(session, scope)
        # load_fx_rate_series wraps FxRateHistoryError in ResourceLoadError via db_resource()
        with pytest.raises(ResourceLoadError) as exc_info:
            await load_fx_rate_series(context)
        cause = exc_info.value.cause
        assert isinstance(cause, FxRateHistoryError)
        assert cause.reason_code == "fx_no_usable_rate"

    @pytest.mark.asyncio
    async def test_fx_technical_coverage_builds_with_partial_signal_history(self, session, test_user):
        """fx.technical_coverage builds successfully even when signal indicators
        have limited history (fewer data points than the full warmup window).

        Seeds rates for only 10 days (shorter than most indicator warmup windows),
        so some signals will be unavailable/zero coverage. The component must
        still build without raising an exception.
        """
        period_start = date(2026, 8, 1)
        period_end = date(2026, 8, 10)

        for offset in range((period_end - period_start).days + 1):
            day = period_start + timedelta(days=offset)
            await _seed_rate(session, base="EUR", quote="USD", rate=str(Decimal("1.10") + Decimal(offset) / Decimal(100)), day=day)

        scope = _scope(user_id=test_user.id, base="EUR", quote="USD", target="EUR", start=period_start, end=period_end)
        context = _fx_technical_context(session, scope)
        # Should not raise even with limited history
        envelope = await context.resolve("fx.technical_coverage", required=True)
        assert envelope is not None
        payload = envelope.payload
        # single-entity selected count must be at least 1 (the FX pair itself)
        assert payload["selected_entity_count"] >= 1

    @pytest.mark.asyncio
    async def test_three_month_source_history_includes_short_signals_and_omits_long_ones(self, session, test_user):
        """A 1Y request backed by only 93 days computes against the available span.

        Shorter-horizon signals remain usable as PARTIAL results while long warm-up
        instances remain explicitly unavailable; the component still succeeds.
        """
        requested_start = date(2032, 1, 1)
        available_start = date(2032, 10, 1)
        period_end = date(2033, 1, 1)
        for offset in range((period_end - available_start).days + 1):
            day = available_start + timedelta(days=offset)
            await _seed_rate(session, base="XPF", quote="CLP", rate=str(Decimal("7.10") + Decimal(offset) / Decimal(10_000)), day=day)

        scope = _scope(user_id=test_user.id, base="XPF", quote="CLP", target="XPF", start=requested_start, end=period_end)
        context = _fx_technical_context(session, scope)
        bundle = await technical_shared_module.load_fx_technical_bundle(context)
        envelope = await context.resolve("fx.technical_coverage", required=True)
        assert envelope is not None

        signal_rows = {row["instance_id"]: row for row in envelope.payload["signals"]}
        result_details = {
            result.instance_id: {
                "status": result.status,
                "warmup": result.warmup,
                "availability": result.availability,
            }
            for result in bundle.signal_results
        }
        assert signal_rows["ema_20"]["partial_count"] == 1, result_details
        assert signal_rows["rsi_14"]["partial_count"] == 1, result_details
        for instance_id in ("ema_200", "sma_200"):
            assert signal_rows[instance_id]["unavailable_count"] == 1, result_details
            assert signal_rows[instance_id]["omission_reasons"] == {"insufficient_history": 1}, result_details
        assert envelope.payload["entities"][0]["included_signal_count"] == 10
        assert envelope.payload["entities"][0]["omitted_signal_count"] == 2
        assert envelope.payload["covered_entity_count"] == 1


# =============================================================================
# fx.exposure_base_quote - explicit base/quote summary + zero-state (requirement 4)
# =============================================================================


class TestExposureSummary:
    """The preserved rows are never removed; an explicit base/quote rollup and
    `has_direct_quote_exposure`/`has_direct_base_exposure` zero-state are derived
    from them so an analysis never infers "no exposure" from an empty row list."""

    @pytest.mark.asyncio
    async def test_zero_exposure_summary_is_explicit_not_missing(self, session, test_user):
        """No matching rows => explicit computed zero-state (False/0), never "missing data"."""
        await _make_broker(session, test_user, name="ZeroSummaryBroker")
        scope = _scope(user_id=test_user.id, base="EUR", quote="USD", target="EUR", start=date(2025, 1, 1), end=date(2025, 1, 5))
        context = _context(session, scope)
        payload = FxExposureBaseQuotePayload.model_validate((await context.resolve("fx.exposure_base_quote", required=True)).payload)

        assert payload.rows == ()
        summary = payload.summary
        assert summary is not None
        assert summary.has_any_direct_exposure is False
        assert summary.has_direct_base_exposure is False
        assert summary.has_direct_quote_exposure is False
        assert summary.total_row_count == 0
        assert summary.base.row_count == 0 and summary.base.gross_target_amount == Decimal(0)
        assert summary.quote.row_count == 0 and summary.quote.net_target_amount == Decimal(0)
        assert summary.base.role is FxExposureRole.BASE
        assert summary.quote.role is FxExposureRole.QUOTE

    @pytest.mark.asyncio
    async def test_nonzero_quote_exposure_summary_counts_and_totals(self, session, test_user):
        """A real USD (quote) cash balance => has_direct_quote_exposure True with matching totals; rows preserved."""
        broker = await _make_broker(session, test_user, name="QuoteExpBroker")
        await _deposit(session, broker, amount="1000", currency="USD", day=date(2025, 1, 2))
        await _seed_warmup_anchor(session, base="EUR", quote="USD", rate="1.10")
        for offset in range(5):
            await _seed_rate(session, base="EUR", quote="USD", rate="1.10", day=date(2025, 1, 1 + offset))

        scope = _scope(user_id=test_user.id, base="EUR", quote="USD", target="EUR", start=date(2025, 1, 1), end=date(2025, 1, 5))
        context = _context(session, scope)
        payload = FxExposureBaseQuotePayload.model_validate((await context.resolve("fx.exposure_base_quote", required=True)).payload)

        quote_rows = [row for row in payload.rows if row.linked_currency == "USD"]
        assert quote_rows, "expected at least one USD cash exposure row"
        summary = payload.summary
        assert summary.has_direct_quote_exposure is True
        assert summary.quote.row_count == len(quote_rows)
        assert summary.quote.cash_row_count == len(quote_rows)
        assert summary.quote.position_row_count == 0
        expected_net = sum((row.target_amount for row in quote_rows), Decimal(0))
        assert summary.quote.net_target_amount == expected_net
        assert summary.quote.gross_target_amount == sum((abs(row.target_amount) for row in quote_rows), Decimal(0))
        # rows themselves are untouched by summarization
        assert len(payload.rows) == summary.total_row_count

    @pytest.mark.asyncio
    async def test_summary_recomputed_on_revalidation_matches_rows(self, session, test_user):
        """Summary is fully derived: constructing directly from rows equals the builder output."""
        broker = await _make_broker(session, test_user, name="ResummaryBroker")
        await _deposit(session, broker, amount="500", currency="USD", day=date(2025, 1, 2))
        await _seed_warmup_anchor(session, base="EUR", quote="USD", rate="1.10")
        for offset in range(5):
            await _seed_rate(session, base="EUR", quote="USD", rate="1.10", day=date(2025, 1, 1 + offset))
        scope = _scope(user_id=test_user.id, base="EUR", quote="USD", target="EUR", start=date(2025, 1, 1), end=date(2025, 1, 5))
        context = _context(session, scope)
        payload = FxExposureBaseQuotePayload.model_validate((await context.resolve("fx.exposure_base_quote", required=True)).payload)

        rebuilt = FxExposureSummary.from_rows(payload.rows, base_currency="EUR", quote_currency="USD", target_currency="EUR")
        assert rebuilt == payload.summary


# =============================================================================
# fx.timing_context - non-predictive observed conversion-timing evidence (goal A)
# =============================================================================


def _timing_registry() -> ComponentRegistry:
    return ComponentRegistry((*FX_CORE_COMPONENTS, *FX_TIMING_CONTEXT_COMPONENTS))


def _timing_context(session, scope: BuildScope) -> BuildContext:
    bucket_plan = build_bucket_plan_for_scope(scope)
    return BuildContext(_timing_registry(), request_id=scope.request_id, scope=scope, bucket_plan=bucket_plan, session=session)


async def _seed_linear_series(session, *, base: str, quote: str, start: date, end: date, first: str, step: str) -> None:
    """Seed a genuine rate every calendar day in [start, end], rate = first + step*offset."""
    first_dec = Decimal(first)
    step_dec = Decimal(step)
    for offset in range((end - start).days + 1):
        day = start + timedelta(days=offset)
        await _seed_rate(session, base=base, quote=quote, rate=str(first_dec + step_dec * offset), day=day)


class TestTimingContextObservedRange:
    @pytest.mark.asyncio
    async def test_increasing_series_current_at_range_maximum(self, session, test_user):
        start, end = date(2027, 3, 1), date(2027, 3, 20)
        await _seed_linear_series(session, base="EUR", quote="USD", start=start, end=end, first="1.10", step="0.01")
        scope = _scope(user_id=test_user.id, base="EUR", quote="USD", target="EUR", start=start, end=end)
        context = _timing_context(session, scope)
        payload = FxTimingContextPayload.model_validate((await context.resolve("fx.timing_context", required=True)).payload)

        rng = payload.observed_range
        assert rng.observed_minimum == Decimal("1.10")
        assert rng.observed_minimum_date == start
        assert rng.observed_maximum_date == end
        # current (as-of end) is the highest observed value => range position 1.0
        assert payload.current_rate == rng.observed_maximum
        assert rng.range_position_ratio == pytest.approx(1.0)
        assert rng.range_position_unavailable_reason is None
        assert rng.distance_to_max_ratio == pytest.approx(0.0)
        assert rng.distance_to_min_ratio > 0
        # observed period return is positive for a strictly increasing series
        assert payload.observed_returns.return_period_ratio is not None and payload.observed_returns.return_period_ratio > 0

    @pytest.mark.asyncio
    async def test_decreasing_series_current_at_range_minimum(self, session, test_user):
        start, end = date(2027, 4, 1), date(2027, 4, 20)
        await _seed_linear_series(session, base="EUR", quote="USD", start=start, end=end, first="1.40", step="-0.01")
        scope = _scope(user_id=test_user.id, base="EUR", quote="USD", target="EUR", start=start, end=end)
        context = _timing_context(session, scope)
        payload = FxTimingContextPayload.model_validate((await context.resolve("fx.timing_context", required=True)).payload)

        rng = payload.observed_range
        assert payload.current_rate == rng.observed_minimum
        assert rng.range_position_ratio == pytest.approx(0.0)
        assert rng.distance_to_min_ratio == pytest.approx(0.0)
        assert rng.distance_to_max_ratio > 0
        assert payload.observed_returns.return_period_ratio is not None and payload.observed_returns.return_period_ratio < 0

    @pytest.mark.asyncio
    async def test_flat_series_range_position_unavailable_with_reason(self, session, test_user):
        start, end = date(2027, 5, 1), date(2027, 5, 10)
        await _seed_linear_series(session, base="EUR", quote="USD", start=start, end=end, first="1.20", step="0")
        scope = _scope(user_id=test_user.id, base="EUR", quote="USD", target="EUR", start=start, end=end)
        context = _timing_context(session, scope)
        payload = FxTimingContextPayload.model_validate((await context.resolve("fx.timing_context", required=True)).payload)

        rng = payload.observed_range
        assert rng.observed_minimum == rng.observed_maximum == Decimal("1.20")
        assert rng.range_position_ratio is None
        assert rng.range_position_unavailable_reason == REASON_FLAT_RANGE
        # a flat series has zero realized volatility and zero period return
        assert payload.observed_returns.return_period_ratio == pytest.approx(0.0)
        assert payload.observed_returns.daily_return_volatility_ratio == pytest.approx(0.0)


class TestTimingContextObservedOnly:
    @pytest.mark.asyncio
    async def test_backfilled_days_excluded_from_observed_stats(self, session, test_user):
        """A gap day is backward-filled: it is counted as backfilled, never as a genuine observation."""
        start, end = date(2027, 6, 1), date(2027, 6, 10)
        gap_day = date(2027, 6, 5)
        for offset in range((end - start).days + 1):
            day = start + timedelta(days=offset)
            if day == gap_day:
                continue  # leave a gap => this visible day backward-fills
            await _seed_rate(session, base="EUR", quote="USD", rate=str(Decimal("1.10") + Decimal(offset) / Decimal(100)), day=day)
        scope = _scope(user_id=test_user.id, base="EUR", quote="USD", target="EUR", start=start, end=end)
        context = _timing_context(session, scope)
        payload = FxTimingContextPayload.model_validate((await context.resolve("fx.timing_context", required=True)).payload)

        # Derive the ground truth directly from the loaded series (robust against any
        # rows other suites may have committed to the shared test DB).
        series = await load_fx_rate_series(context)
        visible = [obs for obs in series.observations if start <= obs.requested_date <= end]
        genuine = [obs for obs in visible if not obs.backward_filled and obs.actual_date == obs.requested_date]
        gap_obs = next(obs for obs in visible if obs.requested_date == gap_day)

        sh = payload.source_history
        assert gap_obs.backward_filled is True  # the gap day carries forward the prior rate
        assert sh.backfilled_observation_count >= 1
        assert sh.observed_observation_count == len(genuine)
        assert sh.observed_observation_count + sh.backfilled_observation_count == len(visible)
        # the backfilled gap date is never an observed extreme date
        assert payload.observed_range.observed_minimum_date != gap_day
        assert payload.observed_range.observed_maximum_date != gap_day

    @pytest.mark.asyncio
    async def test_future_rates_never_consulted(self, session, test_user):
        """Rates seeded after period_end must not influence observed range/returns."""
        start, end = date(2027, 7, 1), date(2027, 7, 10)
        await _seed_linear_series(session, base="EUR", quote="USD", start=start, end=end, first="1.10", step="0.01")
        # A far-higher future rate that must be ignored entirely.
        await _seed_rate(session, base="EUR", quote="USD", rate="9.99", day=date(2027, 7, 20))
        scope = _scope(user_id=test_user.id, base="EUR", quote="USD", target="EUR", start=start, end=end)
        context = _timing_context(session, scope)
        payload = FxTimingContextPayload.model_validate((await context.resolve("fx.timing_context", required=True)).payload)

        assert payload.as_of == end
        assert payload.observed_range.observed_maximum < Decimal("9.99")
        assert payload.observed_range.observed_maximum_date == end
        assert payload.source_history.requested_period_end == end

    @pytest.mark.asyncio
    async def test_missing_user_inputs_always_full_set(self, session, test_user):
        start, end = date(2027, 8, 1), date(2027, 8, 10)
        await _seed_linear_series(session, base="EUR", quote="USD", start=start, end=end, first="1.10", step="0.01")
        scope = _scope(user_id=test_user.id, base="EUR", quote="USD", target="EUR", start=start, end=end)
        context = _timing_context(session, scope)
        payload = FxTimingContextPayload.model_validate((await context.resolve("fx.timing_context", required=True)).payload)

        assert set(payload.missing_user_inputs) == {
            FxNeutralScenarioInput.CONVERSION_AMOUNT,
            FxNeutralScenarioInput.CONVERSION_DEADLINE,
            FxNeutralScenarioInput.EXECUTION_SPREAD,
            FxNeutralScenarioInput.TRANSACTION_FEES,
        }
        # no forecast/predictive band fields exist on the payload
        assert "forecast" not in payload.model_dump()
        assert not any("forecast" in key or "predicted" in key or "band" in key for key in payload.model_dump())

    @pytest.mark.asyncio
    async def test_inverse_pair_current_rate_is_canonical(self, session, test_user):
        """Direction canonical: an inverse-stored pair still yields the quote-per-base current rate."""
        start, end = date(2027, 9, 1), date(2027, 9, 5)
        for offset in range((end - start).days + 1):
            await _seed_rate(session, base="USD", quote="CHF", rate="1.25", day=start + timedelta(days=offset))
        scope = _scope(user_id=test_user.id, base="USD", quote="CHF", target="USD", start=start, end=end)
        context = _timing_context(session, scope)
        payload = FxTimingContextPayload.model_validate((await context.resolve("fx.timing_context", required=True)).payload)
        current = (await context.resolve("fx.current_rate", required=True)).payload
        assert current["direction"] == FxRateDirection.INVERSE.value
        assert payload.current_rate == Decimal("1.25")


class TestTimingContextPartialHistory:
    @pytest.mark.parametrize(
        ("history_days", "expect_1m", "expect_3m"),
        [
            (100, True, True),  # ~3M+ of history: 1M and 3M both available
            (200, True, True),  # ~6M of history
            (370, True, True),  # ~1Y of history
            (20, False, False),  # < 1M of history: short-horizon returns unavailable
        ],
    )
    @pytest.mark.asyncio
    async def test_trailing_returns_available_only_when_history_covers_window(self, session, test_user, history_days, expect_1m, expect_3m):
        period_end = date(2029, 12, 31)
        available_start = period_end - timedelta(days=history_days - 1)
        requested_start = period_end - timedelta(days=400)  # always requests a wide window
        await _seed_linear_series(session, base="XPF", quote="CLP", start=available_start, end=period_end, first="7.10", step="0.001")
        scope = _scope(user_id=test_user.id, base="XPF", quote="CLP", target="XPF", start=requested_start, end=period_end)
        context = _timing_context(session, scope)
        payload = FxTimingContextPayload.model_validate((await context.resolve("fx.timing_context", required=True)).payload)

        sh = payload.source_history
        assert sh.observed_observation_count == history_days
        assert sh.available_start == available_start
        assert sh.is_partial_history is True
        assert sh.complete is False
        assert sh.partial_history_reason == REASON_HISTORY_STARTS_LATE
        assert sh.covered_calendar_days == (period_end - available_start).days + 1
        assert 0 < sh.coverage_ratio < 1
        returns = payload.observed_returns
        assert (returns.return_1m_ratio is not None) is expect_1m
        assert (returns.return_3m_ratio is not None) is expect_3m
        # period return is always available when >= 2 observations exist
        assert returns.return_period_ratio is not None

    @pytest.mark.asyncio
    async def test_complete_history_reports_not_partial(self, session, test_user):
        start, end = date(2029, 1, 1), date(2029, 1, 20)
        await _seed_linear_series(session, base="EUR", quote="USD", start=start, end=end, first="1.10", step="0.001")
        scope = _scope(user_id=test_user.id, base="EUR", quote="USD", target="EUR", start=start, end=end)
        context = _timing_context(session, scope)
        payload = FxTimingContextPayload.model_validate((await context.resolve("fx.timing_context", required=True)).payload)

        sh = payload.source_history
        assert sh.complete is True
        assert sh.is_partial_history is False
        assert sh.partial_history_reason is None
        assert sh.available_start == start
        assert sh.coverage_ratio == pytest.approx(1.0)

    @pytest.mark.asyncio
    async def test_backfilled_period_start_is_still_complete_source_coverage(self, session, test_user):
        start, end = date(2036, 1, 5), date(2036, 1, 12)
        await _seed_rate(session, base="XPF", quote="CLP", rate="7.10", day=start - timedelta(days=1))
        await _seed_linear_series(session, base="XPF", quote="CLP", start=start + timedelta(days=1), end=end, first="7.11", step="0.001")
        scope = _scope(user_id=test_user.id, base="XPF", quote="CLP", target="XPF", start=start, end=end)
        payload = FxTimingContextPayload.model_validate((await _timing_context(session, scope).resolve("fx.timing_context", required=True)).payload)

        sh = payload.source_history
        assert sh.available_start == start
        assert sh.backfilled_observation_count >= 1
        assert sh.complete is True
        assert sh.is_partial_history is False
        assert sh.partial_history_reason is None
        assert sh.coverage_ratio == pytest.approx(1.0)


class TestTimingContextDeterminism:
    @pytest.mark.asyncio
    async def test_identical_output_across_fresh_contexts(self, session, test_user):
        start, end = date(2028, 2, 1), date(2028, 2, 20)
        await _seed_linear_series(session, base="EUR", quote="USD", start=start, end=end, first="1.10", step="0.005")
        scope = _scope(user_id=test_user.id, base="EUR", quote="USD", target="EUR", start=start, end=end)

        first = FxTimingContextPayload.model_validate((await _timing_context(session, scope).resolve("fx.timing_context", required=True)).payload)
        second = FxTimingContextPayload.model_validate((await _timing_context(session, scope).resolve("fx.timing_context", required=True)).payload)
        assert first.model_dump(mode="json") == second.model_dump(mode="json")


# =============================================================================
# Signal coverage partial_reasons (requirement 3)
# =============================================================================


class TestSignalCoveragePartialReasons:
    @pytest.mark.asyncio
    async def test_partial_signals_report_incomplete_warmup_separate_from_omissions(self, session, test_user):
        """A 1Y request backed by ~93 days: short signals are included PARTIAL with an explicit
        `incomplete_warmup` partial reason (separate from omission_reasons), while long warm-up
        instances (ema_200/sma_200) remain omitted/unavailable with `insufficient_history`."""
        requested_start = date(2034, 1, 1)
        available_start = date(2034, 10, 1)
        period_end = date(2035, 1, 1)
        for offset in range((period_end - available_start).days + 1):
            day = available_start + timedelta(days=offset)
            await _seed_rate(session, base="XPF", quote="CLP", rate=str(Decimal("7.10") + Decimal(offset) / Decimal(10_000)), day=day)

        scope = _scope(user_id=test_user.id, base="XPF", quote="CLP", target="XPF", start=requested_start, end=period_end)
        context = _fx_technical_context(session, scope)
        envelope = await context.resolve("fx.technical_coverage", required=True)

        signal_rows = {row["instance_id"]: row for row in envelope.payload["signals"]}
        # Included PARTIAL results carry incomplete_warmup as a partial reason, NOT as an omission.
        for instance_id in ("ema_20", "rsi_14"):
            assert signal_rows[instance_id]["partial_count"] == 1
            assert signal_rows[instance_id]["partial_reasons"] == {"incomplete_warmup": 1}
            assert signal_rows[instance_id]["omission_reasons"] == {}
        # Long warm-up instances remain genuinely omitted (unavailable) - never marked partial-equivalent.
        for instance_id in ("ema_200", "sma_200"):
            assert signal_rows[instance_id]["partial_reasons"] == {}
            assert signal_rows[instance_id]["omission_reasons"] == {"insufficient_history": 1}

        entity = envelope.payload["entities"][0]
        assert entity["included_partial_signal_count"] >= 2
        assert entity["included_partial_signal_count"] <= entity["included_signal_count"]
        assert "incomplete_warmup" in entity["partial_reasons"]

    @pytest.mark.asyncio
    async def test_full_history_has_no_partial_reasons(self, session, test_user):
        """With ample history every included signal is complete OK: no partial reasons at all."""
        start = date(2033, 1, 1)
        end = date(2034, 6, 1)
        await _seed_linear_series(session, base="EUR", quote="USD", start=start, end=end, first="1.10", step="0.0002")
        scope = _scope(user_id=test_user.id, base="EUR", quote="USD", target="EUR", start=date(2034, 5, 1), end=end)
        context = _fx_technical_context(session, scope)
        envelope = await context.resolve("fx.technical_coverage", required=True)

        entity = envelope.payload["entities"][0]
        assert entity["included_partial_signal_count"] == 0
        assert entity["partial_reasons"] == {}
        for row in envelope.payload["signals"]:
            assert row["partial_reasons"] == {}
